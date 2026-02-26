import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual
from services.ai_service import call_groq_json

router = APIRouter(prefix="/api/v1", tags=["Gen Insights"])

class InsightsRequest(BaseModel):
    tema: str
    publico: str
    tom: str

@router.post("/gen-insights")
async def process_insights(
    req: InsightsRequest, 
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    # 1. VALIDAÇÃO DE USUÁRIO E SALDO
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.tema:
        raise HTTPException(status_code=400, detail="O campo Nicho ou Tema é obrigatório.")

    # Definimos o custo dessa ferramenta (1 coin = 1 Ideação Completa)
    custo_operacao = 1

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coin para mapear ideias.")

    # 2. PREPARANDO A INTELIGÊNCIA ARTIFICIAL
    system_prompt = """Você é um roteirista viral especialista em canais Dark do YouTube e TikTok. O usuário te dará um Nicho, Público e Tom. Gere 3 ideias brilhantes e virais de vídeos.

REGRAS DE SAÍDA:
Você DEVE retornar APENAS um objeto JSON válido, sem nenhum texto antes ou depois. O JSON deve ter a seguinte estrutura exata:
{
  "ideias": [
    {
      "titulo": "Título magnético e clicável",
      "gancho": "A promessa ou curiosidade dos primeiros 5 segundos para reter a atenção",
      "resumo": "Um resumo de 3 linhas do que vai acontecer no vídeo"
    }
  ]
}"""

    user_content = f"Nicho/Tema: {req.tema}\nPúblico: {req.publico}\nTom: {req.tom}"

    try:
        # 3. EXECUTANDO A IA
        resultado_str = await call_groq_json(system_prompt, user_content)
        resultado_json = json.loads(resultado_str)
        
        # 4. TRANSAÇÃO FINANCEIRA E HISTÓRICO (O CORAÇÃO DO SAAS)
        usuario.coins -= custo_operacao
        
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Gen Insights",
            input_usuario=user_content,
            resultado=resultado_str, # Salvamos o JSON cru para não perder nada
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()
        
        # Injetamos o novo saldo na resposta para o Front-end atualizar a tela!
        resultado_json["novo_saldo"] = usuario.coins
        
        return resultado_json

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="A IA sofreu uma alucinação e não retornou os dados corretamente. Tente de novo.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
