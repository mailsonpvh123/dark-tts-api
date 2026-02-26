from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)
    
    # --- SISTEMA DE COINS E TIERS ---
    # Opções: FREE, AVULSO, BASIC, INTER, PLUS, BYOK
    tipo_plano = Column(String, default="FREE") 
    coins = Column(Integer, default=30) # Suficiente para 1 vídeo completo
    
    # --- CONFIGURAÇÕES BYOK ---
    gemini_key = Column(String, nullable=True)
    groq_key = Column(String, nullable=True)
    
    # Controle de status
    plano_ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

class Historico(Base):
    __tablename__ = "historicos"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    ferramenta = Column(String) 
    input_usuario = Column(Text)
    resultado = Column(Text)
    custo_coins = Column(Integer, default=0) # Para controle financeiro
    data_geracao = Column(DateTime(timezone=True), server_default=func.now())
