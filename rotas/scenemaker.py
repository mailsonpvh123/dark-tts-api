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
from services.ai_service import call_groq_json, call_gemini # <-- IMPORTANDO OS DOIS MOTORES

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

        # Construção da String de Contexto Blindada
        instrucoes_finais = req.instrucoes if req.instrucoes.strip() else "Nenhuma instrução específica. Use sua criatividade máxima."
        
        user_content = f"""FORMATO DE MÍDIA: {req.formato}
PROPORÇÃO DA TELA (ASPECT RATIO): {req.proporcao}
ESTILO DE ARTE DOMINANTE: {req.estilo}
RITMO DA EDIÇÃO (CENAS): {req.qtd_prompts}
INSTRUÇÕES ESPECÍFICAS DO DIRETOR: {instrucoes_finais}

ROTEIRO PARA DIREÇÃO:
{req.roteiro}"""
        
        # ==========================================
        # ROTEADOR NEURAL INTELIGENTE (GROQ <-> GEMINI)
        # ==========================================
        # Limite do Groq é 12.000 TPM. Definimos 30.000 caracteres como limite seguro.
        TAMANHO_MAXIMO_GROQ = 30000 
        tamanho_roteiro = len(req.roteiro)
        
        dados_str = ""
        motor_utilizado = "Groq"

        if tamanho_roteiro > TAMANHO_MAXIMO_GROQ:
            # Roteiro gigante detectado: Roteia direto pro Gemini
            motor_utilizado = "Gemini"
            dados_str = await call_gemini(system_prompt, user_content)
        else:
            try:
                # Tenta o Groq para velocidade máxima
                dados_str = await call_groq_json(system_prompt, user_content)
            except Exception as e:
                erro_str = str(e)
                # Se o Groq estourar o limite (413) ou falhar, o Gemini assume automaticamente
                if "413" in erro_str or "Request too large" in erro_str or "Limit" in erro_str:
                    print(f"⚠️ Groq sobrecarregado (Limite TPM). Roteando para o Gemini Flash...")
                    motor_utilizado = "Gemini (Fallback)"
                    dados_str = await call_gemini(system_prompt, user_content)
                else:
                    raise e

        # Limpa o markdown do JSON
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
            texto_historico += f"🪄 Prompt Gerado:\n{cena.get('prompt_gringo', '')}\n"
            texto_historico += "-" * 50 + "\n\n"

        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="SceneMaker",
            input_usuario=f"[{req.formato}] {req.estilo} | Tamanho: {tamanho_roteiro} chars",
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
        print(f"❌ Erro no SceneMaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))
