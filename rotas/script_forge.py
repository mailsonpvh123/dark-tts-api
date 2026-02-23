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

    # 1. Lógica condicional de Canal (Exatamente como estava no seu n8n)
    # Se o nome do canal contiver reddit, porão ou medoteca, usa regras de relato
    if re.search(r'reddit|porão|medoteca', req.canal, re.IGNORECASE):
        regras_especificas = """Regras Específicas para Reddit/Relatos:
- Faça a tradução/adaptação com o mínimo de cortes. Não resuma a essência.
- Mantenha Edits/Coments como 'Atualização 1', 'Atualização 2'. Sem datas.
- Remova nomes de usuários.
- Oculte partes onde o usuário diz não ser o autor original (OP) ou avisos prévios.
"""
    else:
        regras_especificas = """Regras Específicas para Documentário/Mistério/Listas:
- Crie uma narrativa imersiva e profunda.
- REGRAS DE LISTA (TOP 10): Se o roteiro for uma lista, NUNCA inicie os tópicos com números soltos ou secos (ex: '10.', '9. O Caso'). Você DEVE usar formato ordinal em texto corrido: 'Em décimo lugar, temos o bizarro caso...', 'Ocupando a nona posição...', 'No oitavo lugar da nossa lista...'. O TTS não entona números secos corretamente.
"""

    # 2. Montagem do Prompt Base de Direção
    prompt_sistema = f"""Você é um Diretor de Roteiro Sênior para canais Dark do YouTube. Sua função é criar roteiros hipnóticos, perfeitamente adaptados para narração por IA (Edge TTS).

🧠 MÓDULO 1: ADAPTAÇÃO AO CANAL E FORMATO ({req.canal})
{regras_especificas}
⚙️ MÓDULO 2: OTIMIZAÇÃO EDGE TTS (O BUG DO SOTAQUE E PROSÓDIA)
O motor Multilingual possui um defeito: sentenças curtas (menos de 6 palavras) e perguntas curtas forçam um sotaque estrangeiro bizarro. VOCÊ TEM A OBRIGAÇÃO DE IMPEDIR ISSO:
- PROIBIDO FRASES CURTAS E PERGUNTAS RÁPIDAS: Nunca use perguntas retóricas curtas como 'O que significava?' ou 'Foi um erro?'. Em vez disso, use frases longas: 'O verdadeiro significado por trás dessa mensagem permanece um grande enigma até os dias de hoje'.
- AGLUTINAÇÃO OBRIGATÓRIA: Transforme qualquer exclamação ou diálogo curto em narrativa estendida.
- PONTUAÇÃO E LIMPEZA: O texto deve ser 100% liso. ZERO markdown (*, #). ZERO emojis. ZERO rubricas.

📏 MÓDULO 3: CONTROLE ESTRITO DE TAMANHO (REGRA DE OURO)
- O usuário solicitou o tamanho exato de: [{req.tamanho}].
- ATENÇÃO: Modelos de IA têm a péssima tendência de gerar texto em excesso. É ESTRITAMENTE PROIBIDO ultrapassar a meta solicitada em mais de 100 palavras. Calcule mentalmente a extensão de cada tópico/parágrafo para fechar o roteiro cirurgicamente no tamanho pedido. Não adicione tópicos extras. Seja objetivo.
- Inicie com Gancho e CTA rápido. Termine com CTA final.

Retorne APENAS o texto final liso, sem formatação JSON, sem introduções."""

    # 3. Conteúdo do Usuário
    user_content = f"""DADOS DO PROJETO:
- Canal: {req.canal}
- Formato: {req.formato}
- Meta de Tamanho: {req.tamanho}
- Tom: {req.tom}
- Instruções Extras: {req.instrucoes}

TEXTO ORIGINAL / IDEIA BASE:
{req.ideia_base}"""

    try:
        # Chama o nosso motor Gemini unificado
        resultado = await call_gemini(system_prompt=prompt_sistema, user_content=user_content)
        return {"roteiro": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
