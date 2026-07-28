from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from app.banco_dados import motor_banco, Base, SessaoLocal
# Importar modelos para garantir a criação das tabelas
from app.modelos import Conteudo, Zona
from app.rotas import admin, tv, usuarios

# Cria as tabelas no banco de dados
Base.metadata.create_all(bind=motor_banco)

# Garante que a zona RU exista por padrão no sistema
with SessaoLocal() as banco:
    zona_ru = banco.query(Zona).filter(Zona.nome == "RU").first()
    if not zona_ru:
        banco.add(Zona(nome="RU"))
        banco.commit()

app = FastAPI(title="Painel ASCOM Digital Signage", description="Gerenciador de Mural Digital UTFPR", version="1.3.1")

# Configura o diretório de dados persistentes para servir as mídias salvas pelas rotas
DIRETORIO_MIDIAS = "./dados/midias"
os.makedirs(DIRETORIO_MIDIAS, exist_ok=True)

app.mount("/midias", StaticFiles(directory=DIRETORIO_MIDIAS), name="midias")

# Monta os estáticos da aplicação (CSS, JS)
DIRETORIO_ESTATICOS = "./app/estaticos"
os.makedirs(DIRETORIO_ESTATICOS, exist_ok=True)
app.mount("/estaticos", StaticFiles(directory=DIRETORIO_ESTATICOS), name="estaticos")

@app.get("/saude")
def checar_saude():
    return {"status": "ok", "mensagem": "Sistema de Mural Digital funcionando corretamente."}

templates = Jinja2Templates(directory="app/visoes")

@app.exception_handler(404)
async def pagina_nao_encontrada(requisicao: Request, exc: Exception):
    """Tratador global de paginas inexistentes devolvendo erro HTML personalizado."""
    return templates.TemplateResponse("404.html", {"request": requisicao}, status_code=404)

# Inclusão das rotas de negócio da ASCOM
app.include_router(tv.roteador)
app.include_router(admin.roteador)
app.include_router(usuarios.roteador)

from fastapi.responses import FileResponse
@app.get("/sw.js", include_in_schema=False)
def servir_service_worker():
    return FileResponse("app/sw.js", media_type="application/javascript")
