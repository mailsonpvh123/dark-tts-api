import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["Meta & SEO"])

class SeoRequest(BaseModel):
    conteudo: str
    keyword: str
    canal: str

@router.post("/meta-seo")
async def process_seo(req: SeoRequest):
    if not req.conteudo:
        raise HTTPException(status_code=400, detail="O roteiro ou conteúdo é obrigatório.")

    system_prompt = """Você é um Especialista Sênior em SEO para YouTube.
Sua missão é extrair a essência do roteiro enviado e criar Metadados (Títulos, Descrição e Tags) altamente virais e otimizados para o algoritmo do YouTube.

ENTREGUE O RESULTADO EM TEXTO PLANO NESTE FORMATO EXATO:

🔥 OPÇÕES DE TÍTULOS (ALTO CTR):
1. [Título magnético 1]
2. [Título magnético 2]
3. [Título magnético 3]

📝 DESCRIÇÃO OTIMIZADA:
[Crie uma descrição persuasiva (2 a 3 parágrafos) usando as palavras-chave naturalmente. Inclua um forte Call to Action (CTA) para inscrição e likes no canal]

🏷️ TAGS PARA O ALGORITMO:
[Gere de 15 a 20 tags separadas por vírgula, das mais abrangentes para as mais específicas de cauda longa]"""

    user_content = f"Canal: {req.canal}\nPalavra-chave Foco: {req.keyword}\n\nROTEIRO/CONTEÚDO:\n{req.conteudo}"

    try:
        # Usando o Gemini que aguenta os roteiros de 15 minutos tranquilamente
        resultado = await call_gemini(system_prompt, user_content)
        
        return {"status": "sucesso", "seo_result": resultado.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
