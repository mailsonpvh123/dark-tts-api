import os
import json
import re
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["SceneMaker"])

class SceneMakerRequest(BaseModel):
    roteiro: str
    formato: str  # "Imagem" ou "Vídeo"

def ler_prompt_arquivo(nome_arquivo: str) -> str:
    caminho = os.path.join(os.getcwd(), "prompts", nome_arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado na pasta prompts!")
        return ""

@router.post("/scenemaker")
async def process_scenemaker(
    req: SceneMakerRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.roteiro or not req.formato:
        raise HTTPException(status_code=400, detail="O roteiro e o formato são obrigatórios.")

    custo_operacao = 15

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Necessário {custo_operacao} coins.")
    
    # Deduz os coins
    usuario.coins -= custo_operacao
    db.commit()

    try:
        system_prompt = ler_prompt_arquivo("scenemaker.txt")
        if not system_prompt:
            raise Exception("Prompt scenemaker.txt não encontrado na base.")

        user_content = f"FORMATO DESEJADO: {req.formato}\n\nROTEIRO:\n{req.roteiro}"
        
        # Chama a IA Orquestradora
        max_retries = 3
        dados_str = ""
        for attempt in range(max_retries):
            try:
                dados_str = await call_gemini(system_prompt, user_content)
                break
            except Exception as e_api:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise e_api

        # Limpa o markdown do JSON (Proteção blindada)
        match = re.search(r'```json\s*(.*?)\s*```', dados_str, re.DOTALL)
        if match:
            dados_str = match.group(1)
        
        try:
            dados_json = json.loads(dados_str)
        except json.JSONDecodeError:
            raise Exception("A IA falhou em estruturar as cenas. Tente gerar novamente.")

        # ==========================================
        # CONSTRÓI O ARQUIVO PARA O HISTÓRICO
        # ==========================================
        texto_historico = "🎬 SCENEMAKER - DIREÇÃO DE ARTE\n\n"
        texto_historico += f"🎥 Formato: {req.formato}\n"
        texto_historico += "=" * 50 + "\n\n"
        
        for i, cena in enumerate(dados_json.get("cenas", [])):
            texto_historico += f"🎞️ CENA {i+1}\n"
            texto_historico += f"🗣️ Fala: \"{cena.get('trecho_narrado', '')}\"\n"
            texto_historico += f"🎬 Ação: {cena.get('acao', '')}\n"
            texto_historico += f"🎥 Câmera: {cena.get('camera', '')}\n"
            texto_historico += f"💡 Luz: {cena.get('iluminacao', '')}\n"
            texto_historico += f"🪄 Prompt Gerado:\n{cena.get('prompt_gringo', '')}\n"
            texto_historico += "-" * 50 + "\n\n"

        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="SceneMaker",
            input_usuario=f"Formato: {req.formato} | Tamanho: {len(req.roteiro)} chars",
            resultado=texto_historico.strip(), 
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {
            "status": "sucesso", 
            "dados": dados_json, 
            "novo_saldo": usuario.coins
        }

    except Exception as e:
        # Reembolsa em caso de falha no motor neural
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no SceneMaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))
