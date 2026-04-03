import json
import re
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

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
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.roteiro or not req.titulo:
        raise HTTPException(status_code=400, detail="Título e roteiro são obrigatórios.")

    custo_operacao = 15

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para gerar ideias de Thumbnail.")

    system_prompt = """You are a world-class YouTube Art Director specializing in high-CTR, emotionally charged thumbnails. 
The user will provide inputs in PORTUGUESE. You MUST return a JSON containing..."""

    user_content = f"TÍTULO DO VÍDEO: {req.titulo}\n\nROTEIRO/RESUMO:\n{req.roteiro}\n\nESTILO VISUAL DESEJADO: {req.estilo}"

    try:
        # ==========================================
        # RETRY COM EXPONENTIAL BACKOFF
        # ==========================================
        max_retries = 3
        dados_str = ""
        
        for attempt in range(max_retries):
            try:
                dados_str = await call_gemini(system_prompt, user_content)
                break
            except Exception as e_api:
                err_msg = str(e_api).lower()
                if "503" in err_msg or "429" in err_msg or "unavailable" in err_msg or "demand" in err_msg:
                    if attempt < max_retries - 1:
                        espera = 2 * (2 ** attempt)
                        print(f"⚠️ Motor Ocupado (Thumb Maker). A aguardar {espera}s... (Tentativa {attempt+1}/{max_retries})")
                        await asyncio.sleep(espera)
                    else:
                        raise Exception("A Dark Neural Engine está sob tráfego extremo neste momento. Por favor, aguarde uns segundos e tente novamente.")
                else:
                    raise e_api

        # O resto do seu código de parse JSON continua intocável
        match = re.search(r'```json\s*(.*?)\s*```', dados_str, re.DOTALL)
        if match:
            dados_str = match.group(1)
        
        dados_json = json.loads(dados_str)
        
        usuario.coins -= custo_operacao
        
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
        
        dados_json["novo_saldo"] = usuario.coins
        return dados_json
        
    except Exception as e:
        print(f"❌ Erro no Thumb Maker: {e}")
        raise HTTPException(status_code=500, detail=str(e))
