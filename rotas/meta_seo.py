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

    # O Prompt de Elite focado em gabaritar 50/50 no VidIQ
    system_prompt = f"""Você é um mestre em SEO para YouTube e copywriter de canais Dark, especialista em gabaritar a pontuação do VidIQ (50/50). Sua missão é ler o roteiro fornecido e criar 5 PACOTES COMPLETOS de SEO otimizados para o canal '{req.canal}'.

REGRAS ABSOLUTAS DO VIDIQ:
1. CONTAGEM DE TAGS: Você deve fornecer exatas 20 tags.
2. VOLUME DE TAGS (5/5): A maioria das tags deve ter alto volume de busca no YouTube.
3. PALAVRAS-CHAVE NO TÍTULO (5/5): As principais palavras-chave das tags DEVEM estar no Título.
4. PALAVRAS-CHAVE NA DESCRIÇÃO (5/5): As palavras-chave do Título e das Tags DEVEM aparecer naturalmente nos primeiros 2 parágrafos da Descrição.
5. PALAVRAS-CHAVE TRIPLAS (5/5): A palavra-chave principal e as secundárias devem estar presentes, EXATAMENTE IGUAIS, no Título, na Descrição e nas Tags.

O QUE VOCÊ DEVE ENTREGAR:
Gere 5 PACOTES distintos. Cada pacote deve conter:
- TÍTULO: (Clickbait, magnético, usando a palavra-chave principal e respeitando o limite de caracteres).
- DESCRIÇÃO: (2 a 3 parágrafos envolventes usando as tags naturalmente, sem parecer lista. Inclua um Call to Action forte para likes e inscrição).
- TAGS: (Exatas 20 tags separadas por vírgula).

FORMATO DE SAÍDA OBRIGATÓRIO:
Entregue apenas o texto limpo, separado exatamente por estes blocos:

[PACOTE 1]
TÍTULO: 
DESCRIÇÃO: 
TAGS: 

[PACOTE 2]
...
(Vá até o PACOTE 5)"""

    user_content = f"Palavra-chave Foco Sugerida pelo Usuário: {req.keyword}\n\nROTEIRO/CONTEÚDO PARA ANÁLISE:\n{req.conteudo}"

    try:
        # Mantendo o Gemini 2.5 Flash, que aguenta analisar roteiros de 15+ minutos sem falhar
        resultado = await call_gemini(system_prompt, user_content)
        
        return {"status": "sucesso", "seo_result": resultado.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
