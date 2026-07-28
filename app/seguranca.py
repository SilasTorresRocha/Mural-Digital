import os
import secrets
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from app.banco_dados import obter_banco
from app.modelos import Usuario

seguranca_basica = HTTPBasic()

# O superusuário administrador que sempre funciona configurado pelo Container
USUARIO_ADMIN = os.getenv("USUARIO_ADMIN", "admin")
SENHA_ADMIN = os.getenv("SENHA_ADMIN", "Tessera1234")

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha_plana.encode('utf-8'), senha_hash.encode('utf-8'))
    except Exception:
        return False

def obter_hash_senha(senha_plana: str) -> str:
    sal = bcrypt.gensalt()
    senha_hasheada = bcrypt.hashpw(senha_plana.encode('utf-8'), sal)
    return senha_hasheada.decode('utf-8')

def verificar_credenciais(credenciais: HTTPBasicCredentials = Depends(seguranca_basica), banco: Session = Depends(obter_banco)):
    """Verifica usuário do ENV, ou faz fallback para os registros criptografados em Banco"""
    # 1. Checa a existência estática e absoluta do sistema
    esta_correto_usuario_master = secrets.compare_digest(credenciais.username, USUARIO_ADMIN)
    esta_correto_senha_master = secrets.compare_digest(credenciais.password, SENHA_ADMIN)
    
    if esta_correto_usuario_master and esta_correto_senha_master:
        return credenciais.username
        
    # 2. Busca entre os usuários dinâmicos cadastrados via painel web 
    usuario_db = banco.query(Usuario).filter(Usuario.login == credenciais.username).first()
    if usuario_db and verificar_senha(credenciais.password, usuario_db.senha_hash):
        return usuario_db.login
        
    # Nenhuma das barreiras aceitou as credenciais
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Basic"},
    )
