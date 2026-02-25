from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["Script Forge"])

class ScriptRequest(BaseModel):
    ideia_base: str
    canal: str
    formato: str
    tamanho: str
    tom: str
    instrucoes: str

@router.post("/script-forge")
async def process_script(req: ScriptRequest):
    if not req.ideia_base:
        raise HTTPException(status_code=400, detail="A ideia base é obrigatória.")

    # Um prompt universal e inteligente, feito para um SaaS que atende qualquer nicho
    regras_gerais = f"""Você é um Roteirista Viral de Elite. Sua função é forjar roteiros magnéticos e com altíssima retenção para YouTube e TikTok.
O usuário (seu cliente) está pedindo um roteiro focado no canal / tema: '{req.canal}'.

REGRAS ABSOLUTAS DE FORJA:
1. TOM E ESTILO: Adapte rigorosamente a escrita para o tom solicitado: [{req.tom}].
2. FORMATO: O formato do vídeo será: [{req.formato}]. Crie ganchos adequados para esse formato.
3. TAMANHO ALVO: A meta de tamanho/duração solicitada é: [{req.tamanho}]. Calcule a estrutura para cumprir rigorosamente esse objetivo. Não enrole (encher linguiça) e não seja curto demais.
4. ESTRUTURA VIRAL:
   - Inicie com um Hook (Gancho) absurdo nos primeiros 5 segundos.
   - Desenvolva o roteiro sem pausas mortas. Mantenha o usuário ansioso pelo que vem a seguir.
   - Termine com um Call to Action (CTA) forte e natural.
5. PREPARO PARA VOZ NEURAL (EDGE TTS): Escreva parágrafos limpos. EVITE frases muito curtas (menos de 4 palavras) para não quebrar a naturalidade da voz da IA. Aglutine ideias sempre que possível.
6. LIMPEZA TOTAL: ZERO formatação de markdown (*, #). ZERO emojis. ZERO rubricas de cenário (ex: [Corta para a câmera], [Música sobe]). Retorne APENAS o texto narrado, do começo ao fim.
"""

    user_content = f"""DADOS DO PROJETO:
- Canal/Nicho: {req.canal}
- Formato: {req.formato}
- Meta de Tamanho/Duração: {req.tamanho}
- Tom da Narrativa: {req.tom}
- Instruções Extras do Cliente: {req.instrucoes}

TEXTO ORIGINAL / IDEIA BASE PARA TRANSFORMAR EM ROTEIRO:
{req.ideia_base}"""

    try:
        system_prompt = regras_gerais + "\nRETORNO OBRIGATÓRIO: Entregue APENAS o texto final liso do roteiro narrado. Nada além disso."
        resultado = await call_gemini(system_prompt, user_content)
        
        return {"status": "sucesso", "roteiro": resultado.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
