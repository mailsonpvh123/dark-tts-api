import re
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

    if re.search(r'reddit|porão|medoteca', req.canal, re.IGNORECASE):
        modulo_1_regras = """Regras Específicas para Reddit/Relatos:
- Faça a tradução/adaptação com o mínimo de cortes. Não resuma a essência.
- Mantenha Edits/Coments como 'Atualização 1', 'Atualização 2'. Sem datas.
- Remova nomes de usuários.
- Oculte partes onde o usuário diz não ser o autor original (OP) ou avisos prévios."""
    else:
        modulo_1_regras = """Regras Específicas para Documentário/Mistério/Listas:
- Crie uma narrativa imersiva e profunda.
- REGRAS DE LISTA (TOP 10): Se o roteiro for uma lista, NUNCA inicie os tópicos com números soltos ou secos (ex: '10.', '9. O Caso'). Você DEVE usar formato ordinal em texto corrido: 'Em décimo lugar, temos o bizarro caso...', 'Ocupando a nona posição...'. O TTS não entona números secos corretamente.
- PROIBIDO ANUNCIAR A ORDEM: Nunca avise o espectador que a lista será apresentada em ordem decrescente ou crescente. Apenas inicie a contagem regressiva naturalmente, sem metalinguagem."""

    system_prompt = f"""Você é um Diretor de Roteiro Sênior para canais Dark do YouTube. Sua função é criar roteiros hipnóticos, perfeitamente adaptados para narração por IA (Edge TTS).

🚨 ASSUNTO OBRIGATÓRIO E EXCLUSIVO:
Você está ESTRITAMENTE PROIBIDO de inventar temas. O seu roteiro DEVE ser construído ÚNICA E EXCLUSIVAMENTE com base no assunto fornecido no campo "TEXTO ORIGINAL / IDEIA BASE". Fuga de tema resultará em falha crítica.

🧠 MÓDULO 1: ADAPTAÇÃO AO CANAL E FORMATO ({req.canal})
{modulo_1_regras}

⚙️ MÓDULO 2: OTIMIZAÇÃO EDGE TTS (O BUG DO SOTAQUE E PROSÓDIA)
O motor Multilingual possui um defeito: sentenças curtas (menos de 6 palavras) e perguntas curtas forçam um sotaque estrangeiro bizarro. VOCÊ TEM A OBRIGAÇÃO DE IMPEDIR ISSO:
- PROIBIDO FRASES CURTAS E PERGUNTAS RÁPIDAS: Nunca use perguntas retóricas curtas. Em vez disso, use frases longas.
- AGLUTINAÇÃO OBRIGATÓRIA: Transforme qualquer exclamação ou diálogo curto em narrativa estendida.
- PONTUAÇÃO E LIMPEZA: O texto deve ser 100% liso. ZERO markdown (*, #). ZERO emojis. ZERO rubricas.

📏 MÓDULO 3: CONTROLE ESTRITO DE TAMANHO E PROFUNDIDADE
- O usuário solicitou o tamanho exato de: [{req.tamanho}].
- A DOENÇA DA IA: Modelos de linguagem sofrem de "preguiça" e tendem a resumir e entregar textos curtos. VOCÊ ESTÁ PROIBIDO DE RESUMIR.
- MATEMÁTICA DA LOCUÇÃO: 1 minuto de áudio falado equivale a aproximadamente 150 palavras. Se o usuário pediu 15 minutos, você DEVE gerar pelo menos 2250 palavras. 
- COMO EXPANDIR: Para atingir o tempo, aprofunde-se absurdamente em cada detalhe. Use histórias paralelas, exemplos concretos, reflexões filosóficas, analogias ricas e transições longas e detalhadas entre os tópicos. Faça o texto render com alta densidade de valor, sem enrolação.

Retorne APENAS o texto final liso."""

    user_content = f"""DADOS DO PROJETO:
- Canal: {req.canal}
- Formato: {req.formato}
- Meta de Tamanho: {req.tamanho}
- Tom: {req.tom}
- Instruções Extras: {req.instrucoes}

TEXTO ORIGINAL / IDEIA BASE:
{req.ideia_base}"""

    try:
        resultado = await call_gemini(system_prompt, user_content)
        
        texto_limpo = resultado.strip()
        texto_limpo = texto_limpo.replace('*', '').replace('#', '')
        texto_limpo = texto_limpo.replace('?', '.').replace('!', '.')
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        
        return {"status": "sucesso", "roteiro": texto_limpo}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
