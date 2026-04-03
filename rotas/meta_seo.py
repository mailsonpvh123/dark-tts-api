import os
import re
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Meta & SEO"])

class SeoRequest(BaseModel):
    conteudo: str
    keyword: str
    canal: str

@router.post("/meta-seo")
async def process_seo(
    req: SeoRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.conteudo:
        raise HTTPException(status_code=400, detail="O roteiro ou conteúdo é obrigatório.")

    custo_operacao = 10

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para gerar a arquitetura de SEO.")

    api_key = os.environ.get("GEMINI_API_KEY_FREE") or os.environ.get("GEMINI_API_KEY")
    modelo_texto = os.environ.get("GEMINI_MODEL_TEXT", "gemini-2.5-flash")

    if not api_key:
        raise HTTPException(status_code=500, detail="Chave API (Dark Neural Engine) não configurada no servidor.")

    client = genai.Client(api_key=api_key)

    system_prompt = f"""Você é um mestre em SEO para YouTube e copywriter de canais Dark...
[PACOTE 1]
TÍTULO: 
DESCRIÇÃO: 
TAGS: 
...""" # Instrução omitida para brevidade, manter a mesma na chamada

    user_content = f"Palavra-chave Foco Sugerida pelo Usuário: {req.keyword}\n\nROTEIRO/CONTEÚDO PARA ANÁLISE:\n{req.conteudo}"

    usuario.coins -= custo_operacao
    db.commit()

    try:
        print(f"📈 Iniciando Meta & SEO (Modelo: {modelo_texto} | Chave: FREE). Custo: {custo_operacao} Coins.")

        # ==========================================
        # RETRY COM EXPONENTIAL BACKOFF
        # ==========================================
        max_retries = 3
        texto_limpo = ""
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=modelo_texto,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction="Você é um mestre em SEO para YouTube especialista em VidIQ. Entregue 5 Pacotes com Título, Descrição e Tags baseados no roteiro.",
                        temperature=0.7
                    )
                )
                texto_limpo = response.text.strip()
                break
            except Exception as e_api:
                err_msg = str(e_api).lower()
                if "503" in err_msg or "429" in err_msg or "unavailable" in err_msg or "demand" in err_msg:
                    if attempt < max_retries - 1:
                        espera = 2 * (2 ** attempt)
                        print(f"⚠️ Motor Ocupado (Meta SEO). A aguardar {espera}s... (Tentativa {attempt+1}/{max_retries})")
                        await asyncio.sleep(espera)
                    else:
                        raise Exception("A Dark Neural Engine está sob tráfego extremo neste momento. Por favor, aguarde uns segundos e tente novamente.")
                else:
                    raise e_api
        
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Meta & SEO",
            input_usuario=f"Canal: {req.canal} | Keyword: {req.keyword}\nRoteiro: {req.conteudo[:150]}...",
            resultado=texto_limpo, 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()
        
        return {"status": "sucesso", "seo_result": texto_limpo, "novo_saldo": usuario.coins}
    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no Meta & SEO: {e}")
        raise HTTPException(status_code=500, detail=str(e))
