from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
# Supondo que você criou o ai_service.py como discutimos anteriormente
from services.ai_service import call_gemini 

router = APIRouter(prefix="/api/v1", tags=["Paraphraser"])

class ParaphraserRequest(BaseModel):
    texto: str
    modo: str
    canal: str

@router.post("/paraphraser")
async def process_paraphraser(req: ParaphraserRequest):
    if not req.texto:
        raise HTTPException(status_code=400, detail="Texto vazio")

    # Regras base extraídas do seu n8n
    prompt_base = f"""Você é um roteirista de elite, especialista em adaptar histórias para o canal Dark do YouTube chamado '{req.canal}'.

REGRAS ABSOLUTAS DE TRANSMUTAÇÃO:
1. PROIBIDO RESUMIR: Faça a adaptação com o MÍNIMO de cortes. Mantenha a mesma riqueza de detalhes e a densidade original. Não perca tempo de retenção.
2. O BUG DO SOTAQUE (MUITO IMPORTANTE): O texto será lido por uma voz Neural (Edge TTS). Essas vozes leem frases curtas (menos de 4 palavras) com sotaque gringo estranho. VOCÊ DEVE ELIMINAR TODAS AS FRASES CURTAS. Aglutine-as ou expanda-as. O texto deve ser longo e fluido.
3. LIMPEZA TOTAL TTS: Não use títulos visuais, subtítulos, hiperlinks, marcações markdown (*, #) ou colchetes. Remova os tempos (00:00). Quero um texto 100% liso para copiar e colar no sintetizador de voz.
"""

    # Adicionando a regra específica baseada no MODO escolhido no Front-end
    if req.modo == "reddit":
        prompt_especifico = """
REGRA DO MODO REDDIT:
- Mantenha a estrutura de relato em primeira pessoa.
- Trate as atualizações como 'Atualização 1', 'Atualização 2', sem mencionar datas.
- OCULTE e remova nomes de usuários. Oculte também qualquer parte onde o usuário diz não ser o autor do post original. Foco 100% no relato.
- Adicione um gancho no início que já comece com o Título da história e um Call to Action (Ex: 'Já deixa o like e se inscreve...').
"""
    else:
        prompt_especifico = """
REGRA DO MODO FUGA DE PLÁGIO:
- Faça um 'Deep Rewrite' (Reescrita Profunda). Mude a estrutura das frases, substitua palavras por sinônimos ricos, mas mantenha a essência exata da mensagem original. O objetivo é que o texto passe ileso por qualquer detector de plágio do YouTube.
"""

    system_instruction = prompt_base + prompt_especifico + "\nRETORNO: Entregue APENAS a narração pura e formatada em parágrafos limpos, sem nenhuma introdução sua."

    try:
        # Chama a função que criamos no ai_service.py
        resultado = await call_gemini(system_prompt=system_instruction, user_content=req.texto)
        return {"texto_transmutado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
