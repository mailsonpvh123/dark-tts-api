import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["Paraphraser"])

class ParaphraserRequest(BaseModel):
    texto: str
    modo: str
    canal: str

@router.post("/paraphraser")
async def process_paraphraser(
    req: ParaphraserRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    # 1. VALIDAÇÃO DE SESSÃO E SALDO
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.texto:
        raise HTTPException(status_code=400, detail="Texto vazio")

    # Custo da ferramenta de reescrita profunda
    custo_operacao = 25

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para transmutar este texto.")


    # ==========================================
    # MÓDULO UNIVERSAL TTS (Aplica-se a todos os modos)
    # ==========================================
    prompt_tts_universal = """
REGRAS OBRIGATÓRIAS DE OTIMIZAÇÃO EDGE TTS:
O texto será lido por uma voz Neural Multilingual. Você DEVE fazer adaptações rigorosas para evitar que a IA leia com sotaque gringo ou tom metálico:
- PROIBIDO FRASES CURTAS: Sentenças com menos de 4 palavras e palavras de poucas sílabas (Ex: "Eu sei!", "Não sabia!", "Foi um erro!") forçam a IA a ter sotaque. Você DEVE alongar e aglutinar essas frases (Ex: Transforme "Eu sei" em "Eu tinha plena consciência de toda aquela situação").
- PONTUAÇÃO PLANA: É estritamente PROIBIDO usar ponto de interrogação (?) ou exclamação (!). Troque perguntas por afirmações indiretas e use apenas pontos finais (.).
- TEXTO 100% LISO: Zero formatação Markdown (*, #, etc). Não use títulos ou subtítulos demarcados na resposta.
"""

    # ==========================================
    # MÓDULO DE ESTRUTURA E ESTILO
    # ==========================================
    if req.modo == "reddit":
        prompt_especifico = f"""Você é um roteirista de elite, traduzindo e adaptando relatos gringos para o canal '{req.canal}'.

DIRETRIZES DO MODO REDDIT:
1. Faça a tradução desse texto com o mínimo de adaptações na essência da história. NÃO RESUMA NADA.
2. Oculte a parte do texto onde o usuário se diz não ser o autor original (OP), caso exista. Oculte também qualquer aviso ou pedido de desculpas que tenha antes de a história começar. Vamos focar apenas na história.
3. Mantenha os Edits e Comentários (Coments), mas REMOVA os nomes de usuários de cada comentário.
4. Sobre as atualizações, trate-as como 'Atualização 1', 'Atualização 2', e assim por diante. Não mencione datas.
5. Adicione um gancho com CTA no início. INICIE O GANCHO EXATAMENTE COM O TÍTULO DA HISTÓRIA.
6. Termine o texto com um CTA forte para o canal.
"""
    else:
        prompt_especifico = f"""Você é um roteirista de elite, reescrevendo histórias para o canal '{req.canal}'.

DIRETRIZES DO MODO ZERO PLÁGIO:
1. FUGA DE PLÁGIO (DEEP REWRITE): Mude a estrutura das frases e substitua palavras por sinônimos ricos, mas mantenha a essência exata da mensagem original. O texto DEVE passar ileso por qualquer detector de plágio do YouTube.
2. NÃO RESUMA NADA: Mantenha a densidade e a riqueza de detalhes do texto original.
3. GANCHO E CTA: Inicie a história com um gancho misterioso chamativo e um Call to Action (CTA) para o canal.
4. ENCERRAMENTO: Termine o texto com um CTA final engajando o público.
"""

    # 3. Montagem Final (Junta as regras específicas com a blindagem do TTS)
    system_instruction = prompt_especifico + "\n" + prompt_tts_universal + "\nRETORNO: Entregue APENAS a narração pura, formatada em parágrafos limpos."
    
    user_content = f"Conteúdo Original:\n{req.texto}"

    try:
        resultado = await call_gemini(system_instruction, user_content)
        
        # ==========================================
        # CAMADA 2: PÓS-PROCESSAMENTO DE SEGURANÇA (Raspagem Bruta)
        # ==========================================
        texto_limpo = resultado.strip()
        
        # Garante a eliminação de formatação Markdown
        texto_limpo = texto_limpo.replace('*', '').replace('#', '')
        
        # Garante a eliminação de exclamações e interrogações caso a IA desobedeça
        texto_limpo = texto_limpo.replace('?', '.').replace('!', '.')
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        
        # ==========================================
        # 4. TRANSAÇÃO FINANCEIRA E HISTÓRICO
        # ==========================================
        usuario.coins -= custo_operacao
        
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Paraphraser",
            input_usuario=f"Modo: {req.modo} | Canal: {req.canal}\nTexto: {req.texto[:150]}...",
            resultado=texto_limpo, 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()

        # Devolve o novo saldo junto com o texto reescrito
        return {"status": "sucesso", "texto_transmutado": texto_limpo, "novo_saldo": usuario.coins}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
