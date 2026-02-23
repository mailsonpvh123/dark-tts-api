from fastapi import APIRouter, Body
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["IA"])

PROMPT_BASE = """Você é um roteirista de elite. REGRAS: 1. PROIBIDO RESUMIR. 2. ELIMINE FRASES CURTAS (menos de 6 palavras) para evitar sotaque bizarro no Edge TTS. 3. REMOVA nomes de usuários."""

@router.post("/paraphraser")
async def process_paraphraser(data: dict = Body(...)):
    texto = data.get("texto")
    modo = data.get("modo") # 'plagio' ou 'reddit'
    
    instrucao_extra = ""
    if modo == "reddit":
        instrucao_extra = "Trate como um relato em primeira pessoa do Reddit. Use 'Atualização 1' em vez de datas."
    else:
        instrucao_extra = "Foque em reescrita profunda para 0% de plágio, mantendo o tom profissional."

    system_prompt = f"{PROMPT_BASE} {instrucao_extra}"
    resultado = await call_gemini(system_prompt, texto)
    
    return {"texto_transmutado": resultado}
