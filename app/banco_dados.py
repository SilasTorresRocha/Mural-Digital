from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Determina o caminho do banco persistente considerando a estrutura projetada
CAMINHO_DIRETORIO_DADOS = "./dados"
CAMINHO_BANCO = f"{CAMINHO_DIRETORIO_DADOS}/banco.db"

# Garante a criação da pasta caso a aplicação rode fora do Docker a primeira vez
os.makedirs(CAMINHO_DIRETORIO_DADOS, exist_ok=True)

URL_BANCO_DADOS = f"sqlite:///{CAMINHO_BANCO}"

motor_banco = create_engine(
    URL_BANCO_DADOS, connect_args={"check_same_thread": False}
)

SessaoLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor_banco)

Base = declarative_base()

def obter_banco():
    banco = SessaoLocal()
    try:
        yield banco
    finally:
        banco.close()
