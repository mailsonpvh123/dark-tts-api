import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual
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
async def process_script(
    req: ScriptRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    # 1. VALIDAÇÃO DE SESSÃO E SALDO
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.ideia_base:
        raise HTTPException(status_code=400, detail="A ideia base é obrigatória.")

    # Custo do Roteiro (O peso pesado do SaaS)
    custo_operacao = 25

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para forjar este roteiro.")

    # 2. LÓGICA DE PROMPT (Com o BUG do exagero corrigido)
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

📏 MÓDULO 3: CONTROLE DE TAMANHO (PRECISÃO CIRÚRGICA)
- O usuário solicitou o tamanho alvo de: [{req.tamanho}].
- CÁLCULO BASE: Considere que 1 minuto de áudio falado = 150 palavras. (Ex: 10 minutos = 1500 palavras).
- REGRA DO LIMITE SUPERIOR: IAs tendem a exagerar e encher linguiça quando pedimos vídeos longos. Você está PROIBIDO de ultrapassar o limite pedido. Se o alvo é 3000 palavras, entregue no máximo entre 3000 e 3200 palavras. Se for 15 minutos (2250 palavras), não passe de 2400 palavras. 
- REGRA DO LIMITE INFERIOR: Não seja preguiçoso. Entregue o volume solicitado aprofundando os detalhes, mas conclua a narrativa assim que o alvo numérico for atingido. Sem enrolação infinita.

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
        
        # 3. TRANSAÇÃO FINANCEIRA E HISTÓRICO
        usuario.coins -= custo_operacao
        
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Script Forge",
            input_usuario=user_content,
            resultado=texto_limpo, 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()

        # Devolvemos o roteiro e o novo saldo do usuário
        return {"status": "sucesso", "roteiro": texto_limpo, "novo_saldo": usuario.coins}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
