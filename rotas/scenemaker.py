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
from services.ai_service import call_groq_json, call_openai_json

router = APIRouter(prefix="/api/v1", tags=["SceneMaker"])

class SceneMakerRequest(BaseModel):
    roteiro: str
    formato: str  
    estilo: str
    proporcao: str
    qtd_prompts: str
    instrucoes: str

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

    # ==========================================
    # CÁLCULO DINÂMICO DE CUSTO
    # Base 5 Coins + 1 Coin a cada 2000 caracteres
    # ==========================================
    tamanho_roteiro = len(req.roteiro)
    custo_operacao = 5 + (tamanho_roteiro // 2000)

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Necessário {custo_operacao} coins.")
    
    usuario.coins -= custo_operacao
    db.commit()

    try:
        system_prompt = ler_prompt_arquivo("scenemaker.txt")
        if not system_prompt:
            raise Exception("Prompt scenemaker.txt não encontrado.")

        instrucoes_finais = req.instrucoes if req.instrucoes.strip() else "Nenhuma instrução específica."
        
        user_content = f"""FORMATO DE MÍDIA: {req.formato}
PROPORÇÃO DA TELA (ASPECT RATIO): {req.proporcao}
ESTILO DE ARTE DOMINANTE: {req.estilo}
RITMO DA EDIÇÃO (CENAS): {req.qtd_prompts}
INSTRUÇÕES ESPECÍFICAS DO DIRETOR: {instrucoes_finais}

ROTEIRO PARA DIREÇÃO:
{req.roteiro}"""
        
        TAMANHO_MAXIMO_GROQ = 30000 
        
        dados_str = ""
        motor_utilizado = "Groq"

        if tamanho_roteiro > TAMANHO_MAXIMO_GROQ:
            motor_utilizado = "OpenAI"
            dados_str = await call_openai_json(system_prompt, user_content)
        else:
            try:
                dados_str = await call_groq_json(system_prompt, user_content)
            except Exception as e:
                erro_str = str(e)
                if "413" in erro_str or "Request too large" in erro_str or "Limit" in erro_str:
                    print(f"⚠️ Groq Limite atingido. Usando OpenAI...")
                    motor_utilizado = "OpenAI (Fallback)"
                    dados_str = await call_openai_json(system_prompt, user_content)
                else:
                    raise e

        match = re.search(r'```json\s*(.*?)\s*```', dados_str, re.DOTALL)
        if match:
            dados_str = match.group(1)
        
        try:
            dados_json = json.loads(dados_str)
        except json.JSONDecodeError:
            raise Exception("Erro na estrutura JSON da IA. Tente novamente.")

        texto_historico = f"🎬 SCENEMAKER - DIREÇÃO DE ARTE (Motor: {motor_utilizado})\n\n"
        texto_historico += f"🎥 Formato: {req.formato} | {req.proporcao}\n"
        texto_historico += f"🎨 Estilo: {req.estilo}\n"
        texto_historico += "=" * 50 + "\n\n"
        
        for i, cena in enumerate(dados_json.get("cenas", [])):
            texto_historico += f"🎞️ CENA {i+1}\n"
            texto_historico += f"🗣️ Fala: \"{cena.get('trecho_narrado', '')}\"\n"
            texto_historico += f"🎬 Ação: {cena.get('acao', '')}\n"
            texto_historico += f"🎥 Câmera: {cena.get('camera', '')}\n"
            texto_historico += f"💡 Luz: {cena.get('iluminacao', '')}\n"
            texto_historico += f"🔍 Stock Search: {cena.get('termo_busca_stock', 'N/A')}\n"
            texto_historico += f"🪄 Prompt Gerado:\n{cena.get('prompt_gringo', '')}\n"
            texto_historico += "-" * 50 + "\n\n"

        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="SceneMaker",
            input_usuario=f"[{req.formato}] {req.estilo} | {tamanho_roteiro} chars",
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
        usuario.coins += custo_operacao
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
