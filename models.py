from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)
    
    # Gestão de Créditos (SaaS Premium)
    coins = Column(Integer, default=50) 
    plano = Column(String, default="free") 
    
    # Configurações BYOK (Chaves do Usuário)
    gemini_key = Column(String, nullable=True)
    groq_key = Column(String, nullable=True)
    usa_propria_key = Column(Boolean, default=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class Historico(Base):
    __tablename__ = "historicos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    ferramenta = Column(String) 
    input_usuario = Column(Text)
    resultado = Column(Text)
    data_geracao = Column(DateTime(timezone=True), server_default=func.now())
