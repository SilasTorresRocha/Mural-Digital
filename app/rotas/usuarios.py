from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.banco_dados import obter_banco
from app.modelos import Usuario, Zona
from app.seguranca import verificar_credenciais, obter_hash_senha, USUARIO_ADMIN
from app.auditoria import registrar_auditoria
import traceback

roteador = APIRouter()
templates = Jinja2Templates(directory="app/visoes")

@roteador.get("/usuario", response_class=HTMLResponse)
def painel_usuarios(requisicao: Request, banco: Session = Depends(obter_banco), _usuario: str = Depends(verificar_credenciais)):
    """Apresenta a tela de usuários. Se for o MASTER, exibe a criação/exclusão. Senão, só a troca de senha."""
    # MASTER tem privilégios totais na visão
    eh_master = (_usuario == USUARIO_ADMIN)
    usuarios_db = banco.query(Usuario).all() if eh_master else []
    zonas_db = banco.query(Zona).all() if eh_master else []
    
    return templates.TemplateResponse(
        "usuarios.html", {"request": requisicao, "usuario": _usuario, "eh_master": eh_master, "usuarios": usuarios_db, "zonas": zonas_db}
    )

@roteador.post("/usuario/novo")
def criar_usuario(
    requisicao: Request,
    login: str = Form(...),
    senha: str = Form(...),
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Cria um novo usuário na base (apenas MASTER)"""
    if _usuario != USUARIO_ADMIN:
        return RedirectResponse(url="/usuario?erro=Apenas_o_superadministrador_pode_criar_contas", status_code=status.HTTP_303_SEE_OTHER)
        
    usuario_existente = banco.query(Usuario).filter(Usuario.login == login).first()
    if usuario_existente or login == USUARIO_ADMIN:
        return RedirectResponse(url="/usuario?erro=Esse_usuario_ja_existe", status_code=status.HTTP_303_SEE_OTHER)
        
    novo_usuario = Usuario(login=login, senha_hash=obter_hash_senha(senha))
    banco.add(novo_usuario)
    banco.commit()
    
    ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
    registrar_auditoria(ip_cliente, _usuario, f"Criou o(a) subadministrador(a) '{login}'")
    
    return RedirectResponse(url="/usuario?sucesso=Usuario_Criado", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/usuario/apagar/{id_usuario}")
def apagar_usuario(
    requisicao: Request,
    id_usuario: int,
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Apaga um registro de usuario (apenas MASTER)"""
    if _usuario != USUARIO_ADMIN:
        return RedirectResponse(url="/usuario?erro=Apenas_o_superadministrador_pode_apagar_contas", status_code=status.HTTP_303_SEE_OTHER)
        
    usuario_db = banco.query(Usuario).filter(Usuario.id == id_usuario).first()
    if usuario_db:
        nome_salvo = usuario_db.login
        banco.delete(usuario_db)
        banco.commit()
        
        ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
        registrar_auditoria(ip_cliente, _usuario, f"Apagou o acesso de '{nome_salvo}'")
        
    return RedirectResponse(url="/usuario?sucesso=Usuario_Apagado", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/usuario/mudar_senha")
def mudar_senha(
    requisicao: Request,
    nova_senha: str = Form(...),
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Altera a própria senha. Se for o MASTER, ignora (pois é por ENV)."""
    if _usuario == USUARIO_ADMIN:
        return RedirectResponse(url="/usuario?erro=A_senha_do_superadministrador_deve_ser_alterada_no_Dockerfile_ENV", status_code=status.HTTP_303_SEE_OTHER)
        
    usuario_db = banco.query(Usuario).filter(Usuario.login == _usuario).first()
    if usuario_db:
        usuario_db.senha_hash = obter_hash_senha(nova_senha)
        banco.commit()
        
        ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
        registrar_auditoria(ip_cliente, _usuario, "Alterou a propria senha com sucesso")
        
        return RedirectResponse(url="/usuario?sucesso=Senha_atualizada_com_sucesso", status_code=status.HTTP_303_SEE_OTHER)
        
    return RedirectResponse(url="/usuario?erro=Erro_interno", status_code=status.HTTP_303_SEE_OTHER)

# ==================== ROTAS DE GERENCIAMENTO DE ZONAS ====================

@roteador.post("/zona/nova")
def criar_zona(
    requisicao: Request,
    nome: str = Form(...),
    modelo_tv: str = Form("2"),
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Cria uma nova Zona (apenas MASTER)"""
    if _usuario != USUARIO_ADMIN:
        return RedirectResponse(url="/usuario?erro=Apenas_o_superadministrador_pode_gerenciar_Zonas", status_code=status.HTTP_303_SEE_OTHER)
        
    zona_existente = banco.query(Zona).filter(Zona.nome == nome).first()
    if zona_existente:
        return RedirectResponse(url="/usuario?erro=Essa_zona_ja_existe", status_code=status.HTTP_303_SEE_OTHER)
        
    nova_zona = Zona(nome=nome, modelo_tv=modelo_tv)
    banco.add(nova_zona)
    banco.commit()
    
    ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
    registrar_auditoria(ip_cliente, _usuario, f"Criou a Zona '{nome}'")
    
    return RedirectResponse(url="/usuario?sucesso=Zona_Criada", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/zona/apagar/{id_zona}")
def apagar_zona(
    requisicao: Request,
    id_zona: int,
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Apaga um registro de Zona e desvincula os conteudos relacionados (apenas MASTER)"""
    if _usuario != USUARIO_ADMIN:
        return RedirectResponse(url="/usuario?erro=Apenas_o_superadministrador_pode_gerenciar_Zonas", status_code=status.HTTP_303_SEE_OTHER)
        
    zona_db = banco.query(Zona).filter(Zona.id == id_zona).first()
    if zona_db:
        # A exclusão da Zona fará com que o SQLAlchemy desvincule automaticamente da tabela M:N secundária
        nome_salvo = zona_db.nome
        banco.delete(zona_db)
        banco.commit()
        
        ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
        registrar_auditoria(ip_cliente, _usuario, f"Apagou a Zona '{nome_salvo}' e todos os seus vínculos")
        
    return RedirectResponse(url="/usuario?sucesso=Zona_Apagada_e_Desvinculada", status_code=status.HTTP_303_SEE_OTHER)

@roteador.post("/zona/modelo/{id_zona}")
def alterar_modelo_zona(
    requisicao: Request,
    id_zona: int,
    modelo_tv: str = Form(...),
    banco: Session = Depends(obter_banco),
    _usuario: str = Depends(verificar_credenciais)
):
    """Altera o modelo de tela da Zona especifica"""
    if _usuario != USUARIO_ADMIN:
        return RedirectResponse(url="/usuario?erro=Apenas_o_superadministrador_pode_gerenciar_Zonas", status_code=status.HTTP_303_SEE_OTHER)
        
    if modelo_tv not in ["-1", "0", "1", "2"]:
        return RedirectResponse(url="/usuario?erro=Modelo_Invalido", status_code=status.HTTP_303_SEE_OTHER)
        
    zona_db = banco.query(Zona).filter(Zona.id == id_zona).first()
    if zona_db:
        zona_db.modelo_tv = modelo_tv
        banco.commit()
        
        ip_cliente = requisicao.client.host if requisicao.client else "Desconhecido"
        registrar_auditoria(ip_cliente, _usuario, f"Alterou layout da Zona '{zona_db.nome}' para Modelo {modelo_tv}")
        
    return RedirectResponse(url="/usuario", status_code=status.HTTP_303_SEE_OTHER)
