from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, Request
from sqlalchemy.orm import Session
import models
from database import get_db

# Use a mesma chave que você definiu no main.py
SECRET_KEY = "SUA_CHAVE_MESTRE_ULTRA_SECRETA_DARK_CREATOR"
ALGORITHM = "HS256"

# Motor de segurança estável
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verificar_senha(senha_pura, senha_hash):
    return pwd_context.verify(senha_pura, senha_hash)

def gerar_hash_senha(senha):
    return pwd_context.hash(senha)

def criar_token_acesso(data: dict):
    para_codificar = data.copy()
    # Expira em 7 dias
    expira = datetime.utcnow() + timedelta(days=7)
    para_codificar.update({"exp": expira})
    return jwt.encode(para_codificar, SECRET_KEY, algorithm=ALGORITHM)

# A FUNÇÃO QUE ESTAVA FALTANDO ABAIXO:
async def get_usuario_atual(request: Request, db: Session = Depends(get_db)):
    """Lê o cookie do navegador e retorna o usuário logado"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
        
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    return usuario
