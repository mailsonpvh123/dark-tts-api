import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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

    # 1. A Base Imutável (Extraída do seu n8n original)
    prompt_base = f"""Você é um roteirista de elite, especialista em adaptar e traduzir histórias para canais Dark do YouTube.
Canal Alvo: '{req.canal}'.

REGRAS ABSOLUTAS DE TRANSMUTAÇÃO:
1. PROIBIDO RESUMIR: Faça a tradução e adaptação com o MÍNIMO de cortes. Mantenha a mesma riqueza de detalhes, o mesmo tom e a mesma densidade do texto original. Não perca tempo de retenção.

2. O BUG DO SOTAQUE (MUITO IMPORTANTE): O texto será lido por uma voz Neural Multilingual (Edge TTS). Essas vozes têm um defeito grave: elas leem frases muito curtas (menos de 4 palavras) ou com palavras monossilábicas com sotaque estrangeiro (Ex: 'Eu sei!', 'Não fui eu'). VOCÊ DEVE ELIMINAR TODAS AS FRASES CURTAS. Aglutine-as ou expanda-as. Transforme um 'Eu sei!' em 'Eu tinha plena consciência de toda aquela situação'. O texto deve ser focado em sentenças médias a longas.

3. PONTUAÇÃO: PROIBIDO usar ponto de interrogação (?) ou exclamação (!). Eles acionam um tom metálico na IA. Troque todas as perguntas diretas por afirmações de questionamento. PROIBIDO usar Markdown (*, #).
"""

    # 2. A Lógica Condicional de Acordo com o Modo Escolhido
    if req.modo == "reddit":
        prompt_especifico = """
4. ESTRUTURA REDDIT E AVISOS: Mantenha os Comentários e Edits, mas REMOVA os nomes de usuários. Trate as atualizações como 'Atualização 1', 'Atualização 2', etc., sem mencionar datas. OCULTE e remova qualquer parte onde o usuário diz não ser o autor do post original ou avisos fora da história. Foco 100% no relato.

5. HOOK E CTA: Adicione um gancho no início que já comece com o Título da história acompanhado de um Call to Action (Ex: 'Essa história é bizarra. Já deixa o like e se inscreve no canal...'). Termine o texto com outro CTA final engajando o público.
"""
    else:
        prompt_especifico = """
4. FUGA DE PLÁGIO (DEEP REWRITE): Mude a estrutura das frases, substitua palavras por sinônimos ricos, mas mantenha a essência exata da mensagem original. O objetivo é que o texto passe ileso por qualquer detector de plágio do YouTube. Sem formatação de roteiro, apenas narração pura.
"""

    # 3. Montagem Final
    system_instruction = prompt_base + prompt_especifico + "\nRETORNO: Entregue APENAS a narração pura, formatada em parágrafos limpos."
    
    user_content = f"Conteúdo Original (ALERTA: APLIQUE A CORREÇÃO DE SOTAQUE E AS REGRAS DE RETENÇÃO):\n{req.texto}"

    try:
        resultado = await call_gemini(system_instruction, user_content)
        
        # ==========================================
        # CAMADA 2: PÓS-PROCESSAMENTO DE SEGURANÇA
        # ==========================================
        texto_limpo = resultado.strip()
        texto_limpo = texto_limpo.replace('*', '').replace('#', '')
        texto_limpo = texto_limpo.replace('?', '.').replace('!', '.')
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        
        return {"status": "sucesso", "texto_transmutado": texto_limpo}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
