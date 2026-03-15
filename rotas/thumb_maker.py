import json
import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["Thumb Maker"])

class ThumbRequest(BaseModel):
    titulo: str
    roteiro: str
    estilo: str
    texto_arte: str
    cor_texto: str
    posicao_texto: str

@router.post("/thumb-maker")
async def process_thumb(
    req: ThumbRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    # 1. VALIDAÇÃO DE SESSÃO E SALDO
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.roteiro or not req.titulo:
        raise HTTPException(status_code=400, detail="Título e roteiro são obrigatórios.")

    # Custo da geração de Prompts de Capa
    custo_operacao = 15

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para gerar ideias de Thumbnail.")

    system_prompt = """You are a world-class YouTube Art Director specializing in high-CTR, emotionally charged thumbnails. 
The user will provide inputs in PORTUGUESE (Title, Script, Visual Style, Exact Text Overlay, Text Color, and Text Position). 
Your task is to generate 3 distinct visual concepts for Midjourney (v6).

REQUIREMENTS:
1. conflito_principal: Identifique a âncora emocional ou o maior mistério do roteiro em 1 frase (em Português).
2. capas: Array com 3 ideias de thumbnails.
   - estrategia: Nome curto da estratégia (ex: Ocultação, Choque, Contraste) (em Português).
   - psicologia: Por que isso gera cliques? (em Português).
   - prompt_gringo: O prompt super detalhado EM INGLÊS para o Midjourney. 
     *IMPORTANT FOR PROMPT_GRINGO*: You MUST include instructions for the text generation based on user input. Example: "Typography: The text '[User Text]' written in [User Color] bold font, positioned at the [User Position] of the image".

YOU MUST RETURN ONLY A VALID JSON. NO MARKDOWN, NO EXPLANATIONS.
FORMATO EXATO:
{
  "conflito_principal": "...",
  "capas": [
    {
      "estrategia": "...",
      "psicologia": "...",
      "prompt_gringo": "..."
    }
  ]
}"""

    user_content = f"""Título do Vídeo: {req.titulo}
Estilo Visual Desejado: {req.estilo}

-- INSTRUÇÕES DE TIPOGRAFIA (OVERLAY) --
Texto na Arte: {req.texto_arte}
Cor do Texto: {req.cor_texto}
Posição na Imagem: {req.posicao_texto}

Roteiro Completo:
{req.roteiro[:2000]}""" # Limitamos o roteiro lido só por segurança de tokens

    try:
        resultado = await call_gemini(system_prompt, user_content)
        
        texto_limpo = resultado.strip()
        texto_limpo = re.sub(r'^```json', '', texto_limpo, flags=re.IGNORECASE)
        texto_limpo = re.sub(r'^```', '', texto_limpo)
        texto_limpo = re.sub(r'```$', '', texto_limpo)
        texto_limpo = texto_limpo.strip()
        
        dados_json = json.loads(texto_limpo)
        
        # ==========================================
        # 2. TRANSAÇÃO FINANCEIRA E HISTÓRICO LIMPO
        # ==========================================
        usuario.coins -= custo_operacao
        
        # Convertendo o JSON em um layout humano e elegante
        texto_historico = "🎨 THUMB MAKER - DIREÇÃO DE ARTE\n\n"
        texto_historico += f"🎯 CONFLITO PRINCIPAL: {dados_json.get('conflito_principal', '')}\n"
        texto_historico += "=" * 50 + "\n\n"
        
        for i, capa in enumerate(dados_json.get("capas", [])):
            texto_historico += f"🖼️ CONCEITO {i+1} ({capa.get('estrategia', '')})\n"
            texto_historico += f"🧠 Psicologia: {capa.get('psicologia', '')}\n"
            texto_historico += f"🪄 Prompt Midjourney (Copie abaixo):\n{capa.get('prompt_gringo', '')}\n"
            texto_historico += "-" * 50 + "\n\n"

        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Thumb Maker",
            input_usuario=f"Título: {req.titulo} | Estilo: {req.estilo}",
            resultado=texto_historico.strip(), 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()
        
        # Injeta o novo saldo no JSON de resposta
        dados_json["novo_saldo"] = usuario.coins
        
        return dados_json
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="A IA falhou ao formatar a resposta. Tente clicar em gerar novamente.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
