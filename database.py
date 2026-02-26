from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# O caminho com 4 barras é para o Linux da VPS encontrar a pasta do volume
SQLALCHEMY_DATABASE_URL = "sqlite:////app/data/dark_creator.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Função para conectar ao banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
