import re
import os
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Script Forge"])

class ScriptRequest(BaseModel):
    ideia_base: str
    canal: str
    formato: str
    tamanho: str
    tom: str
    instrucoes: str

def ler_prompt_arquivo(nome_arquivo: str) -> str:
    caminho = os.path.join(os.getcwd(), "prompts", nome_arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado na pasta prompts!")
        return ""

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

    try:
        minutos = int(re.search(r'\d+', req.tamanho).group())
    except:
        minutos = 5

    custo_operacao = max(1, minutos)

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para forjar este roteiro de {minutos} minutos.")

    usuario.coins -= custo_operacao
    db.commit()

    try:
        api_key = os.environ.get("GEMINI_API_KEY_FREE") or os.environ.get("GEMINI_API_KEY")
        modelo_texto = os.environ.get("GEMINI_MODEL_TEXT", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("Chave GEMINI_API_KEY_FREE não configurada no servidor.")

        client = genai.Client(api_key=api_key)

        if re.search(r'reddit|porão|medoteca', req.canal, re.IGNORECASE):
            modulo_1_regras = """Regras Específicas para Reddit/Relatos:
- Faça a tradução/adaptação com o mínimo de cortes. Não resuma a essência.
- Mantenha Edits/Coments como 'Atualização 1', 'Atualização 2'. Sem datas.
- Remova nomes de usuários.
- Oculte partes onde o usuário diz não ser o autor original (OP) ou avisos prévios."""
        else:
            modulo_1_regras = """Regras Específicas para Documentário/Mistério/Listas:
- Crie uma narrativa imersiva focada em storytelling cinematográfico.
- REGRAS DE POSIÇÃO (TOP 10): NUNCA inicie tópicos com números secos.
- 🚨 TOLERÂNCIA ZERO PARA METALINGUAGEM: O roteiro é o que o narrador vai falar. Você está TERMINANTEMENTE PROIBIDO de usar expressões como "nesta lista", "vamos listar". APENAS CONTE A HISTÓRIA."""

        template_prompt = ler_prompt_arquivo("script_forge.txt")
        if not template_prompt:
            raise ValueError("O arquivo script_forge.txt sumiu da pasta prompts!")

        prompt_final = template_prompt.format(
            canal=req.canal if req.canal.strip() else "nosso canal",
            formato=req.formato,
            tamanho=f"{minutos} minutos",
            tom=req.tom,
            instrucoes=req.instrucoes,
            ideia_base=req.ideia_base,
            modulo_1_regras=modulo_1_regras
        )

        print(f"✍️ Iniciando Script Forge (Dinâmico: {minutos} min). Custo: {custo_operacao} Coins.")

        # ==========================================
        # RETRY COM EXPONENTIAL BACKOFF
        # ==========================================
        max_retries = 3
        texto_limpo = ""
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=modelo_texto,
                    contents=prompt_final,
                    config=types.GenerateContentConfig(
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
                        print(f"⚠️ Motor Ocupado (Script Forge). A aguardar {espera}s... (Tentativa {attempt+1}/{max_retries})")
                        await asyncio.sleep(espera)
                    else:
                        raise Exception("A Dark Neural Engine está sob tráfego extremo neste momento. Por favor, aguarde uns segundos e tente novamente.")
                else:
                    raise e_api
        
        texto_limpo = texto_limpo.replace('*', '').replace('#', '')
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Script Forge",
            input_usuario=f"Canal: {req.canal} | Tempo: {minutos} min",
            resultado=texto_limpo, 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "roteiro": texto_limpo, "novo_saldo": usuario.coins}
        
    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no Script Forge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
