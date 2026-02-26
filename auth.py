from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends
from sqlalchemy.orm import Session
import models
from database import get_db

SECRET_KEY = "SUA_CHAVE_SUPER_SECRETA_MUDE_DEPOIS"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha_pura, senha_hash):
    return pwd_context.verify(senha_pura, senha_hash)

def gerar_hash_senha(senha):
    return pwd_context.hash(senha)

def criar_token_acesso(data: dict):
    para_codificar = data.copy()
    expira = datetime.utcnow() + timedelta(days=7)
    para_codificar.update({"exp": expira})
    return jwt.encode(para_codificar, SECRET_KEY, algorithm=ALGORITHM)
