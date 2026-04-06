from fastapi import APIRouter, HTTPException, Depends, Query
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
    ferramenta: str = Query(None, description="Filtrar por ferramenta"),
    pagina: int = Query(1, ge=1, description="Número da página"),
    limite: int = Query(10, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
    
    query = db.query(models.Historico).filter(models.Historico.usuario_id == usuario.id)

    if ferramenta:
         query = query.filter(models.Historico.ferramenta.ilike(f"%{ferramenta}%"))

    # Conta o total ANTES da paginação
    total_registros = query.count()

    # Aplica ordenação, offset e limit
    offset = (pagina - 1) * limite
    registos = query.order_by(desc(models.Historico.data_geracao)).offset(offset).limit(limite).all()
    
    historico_lista = []
    for r in registos:
        data_formatada = r.data_geracao.strftime("%d/%m/%Y %H:%M") if r.data_geracao else "Desconhecida"
        
        # Como o srt é salvo no banco? Assumindo que pode estar no 'resultado' junto com o audio
        # Se você salvou o texto SRT no 'resultado', ou salvou o caminho do SRT?
        # Para garantir compatibilidade com o que temos, vamos separar a string do resultado se necessário no JS.
        
        historico_lista.append({
            "id": r.id,
            "ferramenta": r.ferramenta,
            "input_usuario": r.input_usuario,
            "resultado": r.resultado,
            "custo_coins": r.custo_coins,
            "data_formatada": data_formatada
        })
        
    return {
        "status": "sucesso", 
        "historico": historico_lista,
        "total": total_registros,
        "pagina_atual": pagina,
        "total_paginas": (total_registros + limite - 1) // limite
    }

@router.delete("/historico/{registro_id}")
async def excluir_historico(
    registro_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
        
    registro = db.query(models.Historico).filter(
        models.Historico.id == registro_id, 
        models.Historico.usuario_id == usuario.id
    ).first()
    
    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")
        
    db.delete(registro)
    db.commit()
    
    return {"status": "sucesso", "msg": "Registro excluído com sucesso."}
