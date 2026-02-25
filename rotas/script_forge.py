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

    # 1. Lógica condicional exata do n8n: 
    # Analisa o nome/tema do canal para decidir as regras do Módulo 1
    if re.search(r'reddit|porão|medoteca', req.canal, re.IGNORECASE):
        modulo_1_regras = """Regras Específicas para Reddit/Relatos:
- Faça a tradução/adaptação com o mínimo de cortes. Não resuma a essência.
- Mantenha Edits/Coments como 'Atualização 1', 'Atualização 2'. Sem datas.
- Remova nomes de usuários.
- Oculte partes onde o usuário diz não ser o autor original (OP) ou avisos prévios."""
    else:
        modulo_1_regras = """Regras Específicas para Documentário/Mistério/Listas:
- Crie uma narrativa imersiva e profunda.
- REGRAS DE LISTA (TOP 10): Se o roteiro for uma lista, NUNCA inicie os tópicos com números soltos ou secos (ex: '10.', '9. O Caso'). Você DEVE usar formato ordinal em texto corrido: 'Em décimo lugar, temos o bizarro caso...', 'Ocupando a nona posição...', 'No oitavo lugar da nossa lista...'. O TTS não entona números secos corretamente."""

    # 2. O Prompt Original de Elite importado do n8n
    system_prompt = f"""Você é um Diretor de Roteiro Sênior para canais Dark do YouTube. Sua função é criar roteiros hipnóticos, perfeitamente adaptados para narração por IA (Edge TTS).

🧠 MÓDULO 1: ADAPTAÇÃO AO CANAL E FORMATO ({req.canal})
{modulo_1_regras}

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

    # 3. Empacotando os dados enviados pelo Front-End
    user_content = f"""DADOS DO PROJETO:
- Canal: {req.canal}
- Formato: {req.formato}
- Meta de Tamanho: {req.tamanho}
- Tom: {req.tom}
- Instruções Extras: {req.instrucoes}

TEXTO ORIGINAL / IDEIA BASE:
{req.ideia_base}"""

    try:
        # Chama o Gemini passando as regras estritas
        resultado = await call_gemini(system_prompt, user_content)
        
        # ==========================================
        # CAMADA 2: PÓS-PROCESSAMENTO DE SEGURANÇA (A Raspagem Bruta)
        # ==========================================
        texto_limpo = resultado.strip()
        
        # O Gemini às vezes teima em usar Markdown, então cortamos no Python
        texto_limpo = texto_limpo.replace('*', '').replace('#', '')
        
        # Caso o Gemini gere interrogações ou exclamações que acionam sotaque gringo
        texto_limpo = texto_limpo.replace('?', '.').replace('!', '.')
        
        # Limpa possíveis redundâncias criadas pela substituição
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        
        return {"status": "sucesso", "roteiro": texto_limpo}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
