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
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.ideia_base:
        raise HTTPException(status_code=400, detail="A ideia base é obrigatória.")

    # Custo do Roteiro
    custo_operacao = 25

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para forjar este roteiro.")

    if re.search(r'reddit|porão|medoteca', req.canal, re.IGNORECASE):
        modulo_1_regras = """Regras Específicas para Reddit/Relatos:
- Faça a tradução/adaptação com o mínimo de cortes. Não resuma a essência.
- Mantenha Edits/Coments como 'Atualização 1', 'Atualização 2'. Sem datas.
- Remova nomes de usuários.
- Oculte partes onde o usuário diz não ser o autor original (OP) ou avisos prévios."""
    else:
        modulo_1_regras = """Regras Específicas para Documentário/Mistério/Listas:
- Crie uma narrativa imersiva focada em storytelling cinematográfico.
- REGRAS DE POSIÇÃO (TOP 10): NUNCA inicie tópicos com números secos (ex: '10.', '9. O Caso'). Use texto corrido: 'Em décimo lugar, temos...', 'Ocupando a nona posição...'.
- 🚨 TOLERÂNCIA ZERO PARA METALINGUAGEM: O roteiro é o que o narrador vai falar. Você está TERMINANTEMENTE PROIBIDO de usar expressões como "nesta contagem regressiva", "nesta lista", "vamos listar", ou "em ordem decrescente". Não avise o espectador sobre a estrutura mecânica do vídeo, APENAS CONTE A HISTÓRIA."""

    system_prompt = f"""Você é um Diretor de Roteiro Sênior para canais Dark do YouTube. Sua função é criar roteiros hipnóticos, perfeitamente adaptados para narração por IA (Edge TTS).

🚨 ASSUNTO OBRIGATÓRIO E EXCLUSIVO:
Você está ESTRITAMENTE PROIBIDO de inventar temas. O seu roteiro DEVE ser construído ÚNICA E EXCLUSIVAMENTE com base no assunto fornecido no campo "TEXTO ORIGINAL / IDEIA BASE". Fuga de tema resultará em falha crítica.

🧠 MÓDULO 1: ADAPTAÇÃO AO CANAL E FORMATO ({req.canal})
{modulo_1_regras}

⚙️ MÓDULO 2: OTIMIZAÇÃO EDGE TTS (O BUG DO SOTAQUE E PROSÓDIA)
- PROIBIDO FRASES CURTAS E PERGUNTAS RÁPIDAS: Nunca use perguntas retóricas curtas. Em vez disso, use frases longas e compostas.
- AGLUTINAÇÃO OBRIGATÓRIA: Transforme qualquer exclamação ou diálogo curto em narrativa estendida.
- PONTUAÇÃO E LIMPEZA: O texto deve ser 100% liso. ZERO markdown (*, #). ZERO emojis. ZERO rubricas.

📏 MÓDULO 3: ENGENHARIA DE EXTENSÃO E PROFUNDIDADE (A TÉCNICA DO ZOOM)
- O usuário pediu o seguinte tamanho: [{req.tamanho}].
- 🚨 MATEMÁTICA OBRIGATÓRIA: Para narradores de IA, a leitura natural e com boa retenção (velocidade 1.0x a 1.1x) exige cerca de 160 a 170 palavras por minuto.
- Se o usuário pedir "15 minutos", seu texto DEVE ter RIGOROSAMENTE entre 2400 e 2600 palavras. Menos que 2300 palavras é considerado uma falha crítica.
- COMO ATINGIR ESSA META SEM ENROLAR:
  1. Não faça resumos. Faça "Zoom In". Expanda cada cenário, cada contexto histórico e cada consequência.
  2. Se for uma lista (ex: Top 10), ESCREVA NO MÍNIMO 3 PARÁGRAFOS LONGOS E DENSOS PARA CADA ITEM. O primeiro apresenta o contexto, o segundo desenvolve o conflito/detalhe bizarro, e o terceiro traz a consequência ou reflexão filosófica daquele item.
  3. Descreva cenários como se estivesse pintando um quadro, usando múltiplos adjetivos e analogias comparativas ricas.

Retorne APENAS o texto final liso."""

    user_content = f"""DADOS DO PROJETO:
- Canal: {req.canal}
- Formato: {req.formato}
- Meta de Tamanho: {req.tamanho}
- Tom: {req.tom}
- Instruções Extras do Cliente: {req.instrucoes} (Incorpore a intenção dessas instruções na narrativa, MAS NUNCA fale essas instruções em voz alta no roteiro).

TEXTO ORIGINAL / IDEIA BASE:
{req.ideia_base}"""

    try:
        resultado = await call_gemini(system_prompt, user_content)
        
        texto_limpo = resultado.strip()
        texto_limpo = texto_limpo.replace('*', '').replace('#', '')
        texto_limpo = texto_limpo.replace('?', '.').replace('!', '.')
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        
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

        return {"status": "sucesso", "roteiro": texto_limpo, "novo_saldo": usuario.coins}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
