import json
import re
import os
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

def ler_prompt_arquivo(nome_arquivo: str) -> str:
    """Lê o prompt dinâmico da pasta de prompts"""
    caminho = os.path.join(os.getcwd(), "prompts", nome_arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado na pasta prompts!")
        return ""

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

    # ==========================================
    # CARREGA O PROMPT EXTERNO
    # ==========================================
    system_prompt = ler_prompt_arquivo("thumb_maker.txt")
    if not system_prompt:
        raise HTTPException(status_code=500, detail="O arquivo thumb_maker.txt não foi encontrado no servidor.")

    user_content = f"TÍTULO DO VÍDEO: {req.titulo}\nROTEIRO/RESUMO:\n{req.roteiro}\nESTILO VISUAL: {req.estilo}\nTEXTO NA ARTE: {req.texto_arte}\nCOR DO TEXTO: {req.cor_texto}\nPOSIÇÃO DO TEXTO: {req.posicao_texto}"

    try:
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

        # ==========================================
        # BLINDAGEM DE JSON PARA O FRONTEND
        # ==========================================
        match = re.search(r'
http://googleusercontent.com/immersive_entry_chip/0

Faça o deploy disto! Ao ler o prompt inteiro, a IA agora sabe exatamente as chaves que precisa entregar ao Javascript, e a sua esteira do Gen Insights até à Thumbnail fluirá sem um único gargalo! 🚀🎨
