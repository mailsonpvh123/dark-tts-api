from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Histórico"])

@router.get("/historico")
async def obter_historico(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
    
    # Busca os últimos 100 registos do utilizador, do mais recente para o mais antigo
    registos = db.query(models.Historico)\
                 .filter(models.Historico.usuario_id == usuario.id)\
                 .order_by(desc(models.Historico.data_geracao))\
                 .limit(100).all()
    
    historico_lista = []
    for r in registos:
        # Formata a data para o padrão de Portugal/Brasil (DD/MM/AAAA HH:MM)
        data_formatada = r.data_geracao.strftime("%d/%m/%Y %H:%M") if r.data_geracao else "Desconhecida"
        
        historico_lista.append({
            "id": r.id,
            "ferramenta": r.ferramenta,
            "input_usuario": r.input_usuario,
            "resultado": r.resultado,
            "custo_coins": r.custo_coins,
            "data_geracao": data_formatada
        })
        
    return {"status": "sucesso", "data": historico_lista}
