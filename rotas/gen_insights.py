import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ai_service import call_groq_json

router = APIRouter(prefix="/api/v1", tags=["Gen Insights"])

class InsightsRequest(BaseModel):
    tema: str
    publico: str
    tom: str

@router.post("/gen-insights")
async def process_insights(req: InsightsRequest):
    if not req.tema:
        raise HTTPException(status_code=400, detail="O campo Nicho ou Tema é obrigatório.")

    # 1. Prompt idêntico ao do n8n
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

    # 2. Dados do Usuário
    user_content = f"Nicho/Tema: {req.tema}\nPúblico: {req.publico}\nTom: {req.tom}"

    try:
        # 3. Chamando a IA
        resultado_str = await call_groq_json(system_prompt, user_content)
        
        # 4. Transformando a String devolvida pelo Groq em um dicionário Python (JSON)
        resultado_json = json.loads(resultado_str)
        
        # Como o Groq já retorna a estrutura {"ideias": [...]}, devolvemos direto!
        return resultado_json

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="O Groq não retornou um formato de dados válido.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
