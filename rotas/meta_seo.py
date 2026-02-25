import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
router = APIRouter(prefix="/api/v1", tags=["Meta & SEO"])

GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

class SeoRequest(BaseModel):
    conteudo: str
    keyword: str
    canal: str

@router.post("/meta-seo")
async def process_seo(req: SeoRequest):
    if not req.conteudo:
        raise HTTPException(status_code=400, detail="O roteiro ou conteúdo é obrigatório.")
    if not GROQ_KEY:
        raise HTTPException(status_code=500, detail="Chave GROQ_API_KEY não configurada no servidor.")

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

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"Erro da API Groq: {response.text}")
            
            data = response.json()
            return {"status": "sucesso", "seo_result": data['choices'][0]['message']['content']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
