from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.banco_dados import obter_banco
from app.modelos import Conteudo, Aviso, Configuracao, Zona

roteador = APIRouter()
templates = Jinja2Templates(directory="app/visoes")

@roteador.get("/")
def selecionar_zona(requisicao: Request, banco: Session = Depends(obter_banco)):
    """Página raiz para a TV escolher em qual localidade ela está (ex: RU)."""
    zonas = banco.query(Zona).all()
    # Se não houver zonas, cria dinamicamente o RU para evitar telas travadas
    if not zonas:
        zona_ru = Zona(nome="RU")
        banco.add(zona_ru)
        banco.commit()
        banco.refresh(zona_ru)
        zonas = [zona_ru]
        
    return templates.TemplateResponse(
        "selecao_zona.html", {"request": requisicao, "zonas": zonas}
    )

import os

@roteador.get("/tv")
def pagina_tv(requisicao: Request, zona_id: int, banco: Session = Depends(obter_banco)):
    """Retorna a página HTML que será exibida na TV filtrada pela Zona."""
    zona_existe = banco.query(Zona).filter(Zona.id == zona_id).first()
    if not zona_existe:
        # Fallback de segurança: Se a URL apontar pra uma Zona apagada ou fantasma
        # Ele volta pra raiz, onde o script JS tem o temporizador para conectar na primeira zona
        return RedirectResponse(url="/")
        
    versao = os.getenv("VERSAO", "1.4.3")
    tester = os.getenv("TESTER", "false").lower() == "true"
    latitude = os.getenv("LATITUDE", "-23.55")
    longitude = os.getenv("LONGITUDE", "-51.46")
        
    return templates.TemplateResponse(
        "tv.html", {
            "request": requisicao, 
            "zona_id": zona_id,
            "versao": versao,
            "tester": tester,
            "latitude": latitude,
            "longitude": longitude
        }
    )

@roteador.get("/api/conteudos_tv")
def listar_conteudos_para_tv(zona_id: int, banco: Session = Depends(obter_banco)):
    """API para a TV buscar a lista de conteúdos a serem exibidos de forma assíncrona filtrados pela zona atual."""
    # Busca conteúdos que estejam ativos E que possuam a Zona desejada vinculada
    conteudos = banco.query(Conteudo).join(Conteudo.zonas).filter(
        Conteudo.ativo == True,
        Zona.id == zona_id
    ).all()
    lista_conteudos = []
    for c in conteudos:
        lista_conteudos.append({
            "id": c.id,
            "titulo": c.titulo,
            "tipo_midia": c.tipo_midia,
            "caminho_arquivo": f"/midias/{c.caminho_arquivo}",
            "tempo_exibicao": c.tempo_exibicao
        })
        
    avisos = banco.query(Aviso).join(Aviso.zonas).filter(
        Aviso.ativo == True,
        Zona.id == zona_id
    ).all()
    lista_avisos = [a.texto for a in avisos]
    
    zona = banco.query(Zona).filter(Zona.id == zona_id).first()
    modelo = zona.modelo_tv if zona and zona.modelo_tv else "0"
    
    return {
        "modelo": modelo,
        "avisos": lista_avisos,
        "conteudos": lista_conteudos
    }

