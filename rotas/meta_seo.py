import os
import re
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Meta & SEO"])

class SeoRequest(BaseModel):
    conteudo: str
    keyword: str
    canal: str

def ler_prompt_arquivo(nome_arquivo: str) -> str:
    """Lê o prompt de SEO da pasta de prompts externos"""
    caminho = os.path.join(os.getcwd(), "prompts", nome_arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado na pasta prompts!")
        return ""

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
    modelo_fallback = "gemini-2.5-flash" 

    if not api_key:
        raise HTTPException(status_code=500, detail="Chave API (Dark Neural Engine) não configurada no servidor.")

    client = genai.Client(api_key=api_key)

    # ==========================================
    # CARREGA E FORMATA O PROMPT EXTERNO
    # ==========================================
    template_prompt = ler_prompt_arquivo("meta_seo.txt")
    if not template_prompt:
        raise ValueError("O arquivo meta_seo.txt sumiu da pasta prompts!")
        
    # AQUI ESTÁ A CORREÇÃO: Passando o canal E a keyword para o Python formatar o .txt
    system_prompt = template_prompt.format(canal=req.canal, keyword=req.keyword)

    user_content = f"Palavra-chave Foco Sugerida pelo Usuário: {req.keyword}\n\nROTEIRO/CONTEÚDO PARA ANÁLISE:\n{req.conteudo}"

    usuario.coins -= custo_operacao
    db.commit()

    try:
        print(f"📈 Iniciando Meta & SEO (Modelo: {modelo_texto} | Chave: FREE). Custo: {custo_operacao} Coins.")

        max_retries = 3
        texto_limpo = ""
        modelo_atual = modelo_texto
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=modelo_atual,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt, 
                        temperature=0.7
                    )
                )
                texto_limpo = response.text.strip()
                break 
            except Exception as e_api:
                err_msg = str(e_api).lower()
                if "503" in err_msg or "429" in err_msg or "unavailable" in err_msg or "demand" in err_msg:
                    if attempt < max_retries - 1:
                        if attempt == 0 and modelo_atual != modelo_fallback:
                            print(f"⚠️ Servidores lotados! Trocando a marcha para modelo de Fallback Seguro ({modelo_fallback})...")
                            modelo_atual = modelo_fallback
                            espera = 2
                        else:
                            espera = 5 * (attempt + 1) 
                            
                        print(f"⚠️ Motor Ocupado (Meta SEO). A aguardar {espera}s... (Tentativa {attempt+1}/{max_retries})")
                        await asyncio.sleep(espera)
                    else:
                        raise Exception("A Dark Neural Engine está sob tráfego extremo no Google. Por favor, aguarde 1 minuto e tente novamente.")
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
