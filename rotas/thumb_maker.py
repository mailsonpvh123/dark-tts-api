import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["Thumb Maker"])

class ThumbRequest(BaseModel):
    titulo: str
    roteiro: str
    estilo: str
    texto_arte: str

@router.post("/thumb-maker")
async def process_thumb(req: ThumbRequest):
    if not req.roteiro or not req.titulo:
        raise HTTPException(status_code=400, detail="Título e roteiro são obrigatórios.")

    system_prompt = """You are a world-class YouTube Art Director specializing in high-CTR, emotionally charged thumbnails. 
The user will provide inputs in PORTUGUESE (Title, Script, Visual Style, and Exact Text Overlay). 
Your task is to generate 3 distinct visual concepts for Midjourney/DALL-E.

REQUIREMENTS:
1. conflito_principal: Identifique a âncora emocional ou o maior mistério do roteiro em 1 frase (em Português).
2. capas: Array com 3 ideias de thumbnails.
   - estrategia: Nome curto da estratégia (ex: Ocultação, Choque, Contraste) (em Português).
   - psicologia: Por que isso gera cliques? (em Português).
   - prompt_gringo: O prompt super detalhado EM INGLÊS para o Midjourney. Deve incluir o estilo visual solicitado pelo usuário e ser focado em hiper-realismo ou no estilo pedido.

YOU MUST RETURN ONLY A VALID JSON. NO MARKDOWN, NO EXPLANATIONS.
FORMATO EXATO:
{
  "conflito_principal": "...",
  "capas": [
    {
      "estrategia": "...",
      "psicologia": "...",
      "prompt_gringo": "..."
    }
  ]
}"""

    user_content = f"""Título do Vídeo: {req.titulo}
Estilo Visual Desejado: {req.estilo}
Texto na Arte (Overlay): {req.texto_arte}

Roteiro Completo:
{req.roteiro}"""

    try:
        resultado = await call_gemini(system_prompt, user_content)
        
        # Limpeza bruta: O Gemini às vezes coloca ```json no começo da resposta. Precisamos limpar isso para o Python conseguir ler.
        texto_limpo = resultado.strip()
        texto_limpo = re.sub(r'^```json', '', texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r'^```', '', texto_limpo)
        texto_limpo = re.sub(r'```$', '', texto_limpo)
        texto_limpo = texto_limpo.strip()
        
        dados_json = json.loads(texto_limpo)
        
        return dados_json
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="A IA falhou ao formatar a resposta. Tente clicar em gerar novamente.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
