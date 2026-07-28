import logging
from logging.handlers import RotatingFileHandler
import os

CAMINHO_DIRETORIO_DADOS = "./dados"
os.makedirs(CAMINHO_DIRETORIO_DADOS, exist_ok=True)

CAMINHO_LOG_AUDITORIA = f"{CAMINHO_DIRETORIO_DADOS}/auditoria.log"

# Define um logger especifico para não chocar com o do Uvicorn ou da API
logger_auditoria = logging.getLogger("auditoria")
logger_auditoria.setLevel(logging.INFO)

# Handler rotativo (Máx 5MB arquivo com até 10 backups - evita estourar o hd)
manipulador = RotatingFileHandler(CAMINHO_LOG_AUDITORIA, maxBytes=5*1024*1024, backupCount=10)

# Formato da Mensagem de Log: "[03-03-2026 15:30:12] IP 192.168.0.5 - Admin - Adicionou Video"
formatador = logging.Formatter('[%(asctime)s] IP %(clientip)s - Usuário: %(user)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

manipulador.setFormatter(formatador)
logger_auditoria.addHandler(manipulador)

def registrar_auditoria(ip_cliente: str, usuario: str, acao: str):
    """
    Registra uma ação administrativa no arquivo auditoria.log.
    Ex: registrar_auditoria('127.0.0.1', 'admin', 'Apagou o aviso ID 3')
    """
    logger_auditoria.info(acao, extra={'clientip': ip_cliente, 'user': usuario})
