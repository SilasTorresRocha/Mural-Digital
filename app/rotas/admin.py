import os
import uuid
import logging
import subprocess
from fastapi import APIRouter, Request, Depends, HTTPException, status, File, UploadFile, Form, BackgroundTasks
from fastapi.templating import Jinja2Templates
from PIL import Image
import io
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.banco_dados import obter_banco
from app.modelos import Conteudo, Aviso, Configuracao
from app.seguranca import verificar_credenciais
from app.auditoria import registrar_auditoria

roteador = APIRouter()
templates = Jinja2Templates(directory="app/visoes")

@roteador.get("/config", response_class=HTMLResponse)
def painel_admin(requisicao: Request, banco: Session = Depends(obter_banco), _usuario: str = Depends(verificar_credenciais)):
    """Lista todos os conteudos e avisos cadastrados no painel administrativo."""
    from app.modelos import Zona
    
    conteudos = banco.query(Conteudo).all()
    avisos = banco.query(Aviso).all()
    zonas = banco.query(Zona).all()
        
    return templates.TemplateResponse(
        "admin.html", {
            "request": requisicao, 
            "conteudos": conteudos, 
            "avisos": avisos,
            "zonas": zonas,
            "usuario": _usuario
        }
    )

progresso_videos = {}

def processar_video_bg(tarefa_id: str, caminho_temp: str, caminho_final: str, titulo: str, tempo_exibicao: int, zonas_selecionadas: list, _usuario: str, ip_cliente: str):
    progresso_videos[tarefa_id] = {"status": "iniciando", "progresso": 0}
    
    cmd_probe = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", caminho_temp
    ]
    try:
        res = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duracao_str = res.stdout.strip()
        duracao_total = float(duracao_str) if duracao_str else 0.1
    except Exception as e:
        duracao_total = 0.1
        logging.error(f"Erro no ffprobe: {e}")
    
    comando = [
        "ffmpeg", "-y",
        "-i", caminho_temp,
        # Limita a 1080p (Mantém a qualidade nas TVs 4K, não deforma, e aceita vídeos verticais)
        "-vf", "scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease,format=yuv420p",
        "-r", "30",               # O SEGREDO MÁGICO: Corta para 30 FPS para salvar o TV Stick
        "-c:v", "libx264",
        "-profile:v", "main",     # 'main' entrega qualidade superior sem pesar a CPU do stick
        "-level", "4.0",          # Nível 4.0 suporta 1080p a 30fps tranquilamente
        
        # Controle de Qualidade Inteligente (Substitui o "-b:v")
        "-crf", "23",             # 23 é o padrão ideal. (Menor = mais qualidade/mais pesado. Maior = pior qualidade/mais leve)
        "-maxrate", "4000k",      # Impede picos gigantes de rede que causam aquele engasgo no início
        "-bufsize", "8000k",      # Dá uma "folga" de buffer para o player do Android
        
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        caminho_final
    ]
    
    try:
        processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
        
        for linha in processo.stdout:
            if "out_time_us=" in linha:
                try:
                    micro_segundos = int(linha.split("=")[1].strip())
                    segundos_processados = micro_segundos / 1_000_000
                    
                    porcentagem = (segundos_processados / duracao_total) * 100
                    if porcentagem > 99: porcentagem = 99
                    if porcentagem < 0: porcentagem = 0
                    
                    progresso_videos[tarefa_id] = {"status": "processando", "progresso": round(porcentagem, 1)}
                except:
                    pass
                    
        processo.wait()
        
        if processo.returncode == 0:
            from app.banco_dados import SessaoLocal
            from app.modelos import Conteudo, Zona
            import os
            banco = SessaoLocal()
            try:
                nome_seguro_arquivo = os.path.basename(caminho_final)
                novo_conteudo = Conteudo(
                    titulo=titulo,
                    tipo_midia="video",
                    caminho_arquivo=nome_seguro_arquivo,
                    tempo_exibicao=tempo_exibicao,
                    ativo=True
                )
                
                if not zonas_selecionadas:
                    todas_zonas = banco.query(Zona).all()
                    novo_conteudo.zonas.extend(todas_zonas)
                else:
                    zonas_bd = banco.query(Zona).filter(Zona.nome.in_(zonas_selecionadas)).all()
                    novo_conteudo.zonas.extend(zonas_bd)
                
                banco.add(novo_conteudo)
                banco.commit()
                banco.refresh(novo_conteudo)
                from app.auditoria import registrar_auditoria
                registrar_auditoria(ip_cliente, _usuario, f"Adicionou conteudo '{titulo}' (ID: {novo_conteudo.id})")
            finally:
                banco.close()
            
            progresso_videos[tarefa_id] = {"status": "concluido", "progresso": 100}
        else:
            progresso_videos[tarefa_id] = {"status": "erro", "progresso": 0, "mensagem": "Falha na conversão do vídeo pelo FFmpeg."}
    except Exception as e:
        progresso_videos[tarefa_id] = {"status": "erro", "progresso": 0, "mensagem": str(e)}
        logging.error(f"Erro no FFmpeg: {e}")
    finally:
        if os.path.exists(caminho_temp):
            try: os.remove(caminho_temp)
            except: pass


@roteador.get("/config/progresso/{tarefa_id}")
def obter_progresso(tarefa_id: str):
    progresso = progresso_videos.get(tarefa_id, {"status": "desconhecido", "progresso": 0})
    return JSONResponse(content=progresso)


@roteador.post("/config/novo")
async def adicionar_conteudo(
    requisicao: Request,
    background_tasks: BackgroundTasks,
    titulo: str = Form(...),
    tempo_exibicao: int = Form(10),
    arquivo: UploadFile = File(...),
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Salva a nova mídia e registra no banco de dados com nome em UUID."""
    from app.modelos import Zona
    # O FastAPI Form pode não capturar múltiplas checkboxes iguais dependendo da estruturação, 
    # vai async form puxando a lista de dados da request brutos para evitar bugs de lista única
    form_data = await requisicao.form()
    zonas_selecionadas = form_data.getlist("zonas")
    
    if not arquivo.filename:
        raise HTTPException(status_code=400, detail="Arquivo não fornecido")

    extensao = os.path.splitext(arquivo.filename)[1].lower()
    nome_unico = uuid.uuid4().hex

    eh_video = arquivo.content_type.startswith("video") or extensao in ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
    
    if eh_video:
        caminho_temp = f"./dados/midias/temp_{nome_unico}{extensao}"
        caminho_final = f"./dados/midias/{nome_unico}.mp4"
        
        with open(caminho_temp, "wb") as buffer:
            while conteudo_bloco := await arquivo.read(1024 * 1024):
                buffer.write(conteudo_bloco)
                
        tarefa_id = str(uuid.uuid4())
        background_tasks.add_task(
            processar_video_bg, 
            tarefa_id, 
            caminho_temp, 
            caminho_final, 
            titulo, 
            tempo_exibicao, 
            zonas_selecionadas,
            _usuario, 
            ip_cliente
        )
        return JSONResponse(content={"status": "processando", "tarefa_id": tarefa_id})

    else:
        tipo_midia = "imagem"
        # Padroniza todas as imagens como JPEG para compatibilidade maxima
        nome_seguro_arquivo = f"{nome_unico}.jpg"
        caminho_final = f"./dados/midias/{nome_seguro_arquivo}"
        
        try:
            dados_brutos = await arquivo.read()
            imagem_carregada = Image.open(io.BytesIO(dados_brutos))
            
            # Converte para padrao RGB para garantir formato JPEG
            if imagem_carregada.mode in ("RGBA", "P"):
                imagem_carregada = imagem_carregada.convert("RGB")
                
            # Restringe resolucao maxima a Full HD
            imagem_carregada.thumbnail((1920, 1080))
            
            # Otimiza o peso da imagem
            imagem_carregada.save(caminho_final, "JPEG", quality=85, optimize=True)
        except Exception as erro_imagem:
            logging.error(f"Erro no processamento da imagem {arquivo.filename}: {erro_imagem}")
            raise HTTPException(status_code=400, detail="Falha ao processar arquivo de imagem fornecido.")
            
        novo_conteudo = Conteudo(
            titulo=titulo,
            tipo_midia=tipo_midia,
            caminho_arquivo=nome_seguro_arquivo,
            tempo_exibicao=tempo_exibicao,
            ativo=True
        )
        
        if not zonas_selecionadas:
            todas_zonas = banco.query(Zona).all()
            novo_conteudo.zonas.extend(todas_zonas)
        else:
            zonas_bd = banco.query(Zona).filter(Zona.nome.in_(zonas_selecionadas)).all()
            novo_conteudo.zonas.extend(zonas_bd)
            
        banco.add(novo_conteudo)
        banco.commit()
        
        registrar_auditoria(ip_cliente, _usuario, f"Adicionou conteudo '{titulo}' (ID: {novo_conteudo.id})")
        
        return JSONResponse(content={"status": "concluido"})

@roteador.post("/config/apagar/{id_conteudo}")
def apagar_conteudo(
    requisicao: Request,
    id_conteudo: int,
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Apaga um conteudo do banco de dados e o arquivo persistente, limpando mídia órfã."""
    conteudo = banco.query(Conteudo).filter(Conteudo.id == id_conteudo).first()
    if conteudo:
        # Extrai os dados antes da exclusao
        titulo_salvo = conteudo.titulo
        caminho_arquivo = f"./dados/midias/{conteudo.caminho_arquivo}"
        
        # Limpeza Física do Arquivo
        if os.path.exists(caminho_arquivo):
            try:
                os.remove(caminho_arquivo)
            except Exception as e:
                logging.error(f"Erro ao deletar a midia {caminho_arquivo}: {e}")
                
        # Limpeza Lógica do Banco
        banco.delete(conteudo)
        banco.commit()
        
        ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
        registrar_auditoria(ip_cliente, _usuario, f"Apagou conteudo '{titulo_salvo}' e seu arquivo fisico vinculado.")
        
    return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/config/alternar/{id_conteudo}")
def alternar_status_conteudo(
    id_conteudo: int,
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Alterna se o conteudo está ativo (exibindo na TV) ou não."""
    conteudo = banco.query(Conteudo).filter(Conteudo.id == id_conteudo).first()
    if conteudo:
        conteudo.ativo = not conteudo.ativo
        banco.commit()
    return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)

# ======================= ROTAS DE AVISOS TEXTUAIS =======================

@roteador.post("/config/aviso/novo")
async def adicionar_aviso(
    requisicao: Request,
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    from app.modelos import Zona
    form_data = await requisicao.form()
    texto = form_data.get("texto")
    zonas_selecionadas_aviso = form_data.getlist("zonas_selecionadas_aviso")
    
    if not texto:
        return RedirectResponse(url="/config?erro=Texto_obrigatorio", status_code=status.HTTP_303_SEE_OTHER)
    if len(texto) > 150:
         return RedirectResponse(url="/config?erro=Limite_de_150_caracteres_excedido", status_code=status.HTTP_303_SEE_OTHER)

    novo_aviso = Aviso(texto=texto, ativo=False)
    
    # Vinculador de Zonas do Aviso
    if not zonas_selecionadas_aviso:
        todas_zonas = banco.query(Zona).all()
        novo_aviso.zonas.extend(todas_zonas)
    else:
        zonas_bd = banco.query(Zona).filter(Zona.nome.in_(zonas_selecionadas_aviso)).all()
        novo_aviso.zonas.extend(zonas_bd)
        
    # Verifica se alguma das zonas selecionadas já estourou o limite de 4 ativos
    vai_ativar = True
    for z in novo_aviso.zonas:
        ativos_count = banco.query(Aviso).join(Aviso.zonas).filter(Aviso.ativo == True, Zona.id == z.id).count()
        if ativos_count >= 4:
            vai_ativar = False
            break
            
    novo_aviso.ativo = vai_ativar
        
    banco.add(novo_aviso)
    banco.commit()
    
    ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
    registrar_auditoria(ip_cliente, _usuario, f"Adicionou o aviso '{texto}' (Zonas: {','.join(zonas_selecionadas_aviso) if zonas_selecionadas_aviso else 'Global'})")
    
    # Redireciona com um erro caso tenha salvado desativado
    if not vai_ativar:
        return RedirectResponse(url="/config?erro=Maximo_4_avisos_ativos._O_seu_foi_salvo_como_inativo.", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/config/aviso/apagar/{id_aviso}")
def apagar_aviso(requisicao: Request, id_aviso: int, banco: Session = Depends(obter_banco), _usuario: str = Depends(verificar_credenciais)):
    aviso = banco.query(Aviso).filter(Aviso.id == id_aviso).first()
    if aviso:
        texto_salvo = aviso.texto
        banco.delete(aviso)
        banco.commit()
        ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
        registrar_auditoria(ip_cliente, _usuario, f"Apagou o aviso '{texto_salvo}'")
        
    return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/config/aviso/alternar/{id_aviso}")
def alternar_status_aviso(id_aviso: int, banco: Session = Depends(obter_banco), _usuario: str = Depends(verificar_credenciais)):
    from app.modelos import Zona
    aviso = banco.query(Aviso).filter(Aviso.id == id_aviso).first()
    if aviso:
        if not aviso.ativo:
            # Se ele vai ativar, verificar se o destino permite
            for z in aviso.zonas:
                ativos_count = banco.query(Aviso).join(Aviso.zonas).filter(Aviso.ativo == True, Zona.id == z.id).count()
                if ativos_count >= 4:
                    return RedirectResponse(url=f"/config?erro=A_zona_{z.nome}_ja_atingiu_o_limite_de_4_avisos", status_code=status.HTTP_303_SEE_OTHER)
                
        aviso.ativo = not aviso.ativo
        banco.commit()
    return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)

# ======================= ROTAS DE EDIÇÃO DE ZONAS (INLINE) =======================

@roteador.post("/config/conteudo/{id_conteudo}/zonas")
async def editar_zonas_conteudo(
    requisicao: Request,
    id_conteudo: int,
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Permite alterar os Zonas atreladas a uma mídia já cadastrada."""
    from app.modelos import Zona
    conteudo = banco.query(Conteudo).filter(Conteudo.id == id_conteudo).first()
    if not conteudo:
         return RedirectResponse(url="/config?erro=Conteúdo_não_encontrado", status_code=status.HTTP_303_SEE_OTHER)
         
    form_data = await requisicao.form()
    zonas_selecionadas = form_data.getlist("zonas_editadas")
    
    # Limpa as atuais
    conteudo.zonas.clear()
    
    if not zonas_selecionadas:
        todas_zonas = banco.query(Zona).all()
        conteudo.zonas.extend(todas_zonas)
        str_zonas = "Global"
    else:
        zonas_bd = banco.query(Zona).filter(Zona.nome.in_(zonas_selecionadas)).all()
        conteudo.zonas.extend(zonas_bd)
        str_zonas = ",".join(zonas_selecionadas)
        
    banco.commit()
    ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
    registrar_auditoria(ip_cliente, _usuario, f"Alterou as Zonas do Video '{conteudo.titulo}' para: {str_zonas}")
    return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/config/aviso/{id_aviso}/zonas")
async def editar_zonas_aviso(
    requisicao: Request,
    id_aviso: int,
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Permite alterar os Zonas atreladas a um letreiro já cadastrado."""
    from app.modelos import Zona
    aviso = banco.query(Aviso).filter(Aviso.id == id_aviso).first()
    if not aviso:
         return RedirectResponse(url="/config?erro=Aviso_não_encontrado", status_code=status.HTTP_303_SEE_OTHER)
         
    form_data = await requisicao.form()
    zonas_selecionadas = form_data.getlist("zonas_editadas")
    
    aviso.zonas.clear()
    
    if not zonas_selecionadas:
        todas_zonas = banco.query(Zona).all()
        aviso.zonas.extend(todas_zonas)
        str_zonas = "Global"
    else:
        zonas_bd = banco.query(Zona).filter(Zona.nome.in_(zonas_selecionadas)).all()
        aviso.zonas.extend(zonas_bd)
        str_zonas = ",".join(zonas_selecionadas)
        
    banco.commit()
    ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
    registrar_auditoria(ip_cliente, _usuario, f"Alterou as Zonas do Aviso '{aviso.texto[:20]}...' para: {str_zonas}")
    return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)

@roteador.get("/sair")
def sair_da_conta():
    """Tenta forçar o navegador a esquecer as credenciais via 401."""
    return HTMLResponse(
        content="""
        <html>
        <head>
            <title>Sessão Encerrada</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                body { background: #0f172a; color: white; text-align: center; font-family: 'Inter', sans-serif; margin-top: 15%; }
                a { display: inline-block; padding: 10px 20px; background: #38bdf8; color: #0f172a; text-decoration: none; border-radius: 5px; margin-top: 20px; font-weight: bold; }
                a:hover { background: #0284c7; color: white; }
            </style>
        </head>
        <body>
            <h1>Você Saiu do Painel Administrativo</h1>
            <p>Seu navegador grava senhas inseridas em memória que podem reconectar à Painel silenciosamente.</p>
            <p style="color: #fbbf24;">Por segurança de log-out com 100% de garantia, recomendo agora: fechar totalmente o seu Navegador.</p>
            <a href="/">Retornar à Tela Principal (TV)</a>
        </body>
        </html>
        """,
        status_code=status.HTTP_401_UNAUTHORIZED
    )
