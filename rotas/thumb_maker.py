import json
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
    # CARREGA O PROMPT EXTERNO (COM FALLBACK DE EMERGÊNCIA)
    # ==========================================
    system_prompt = ler_prompt_arquivo("thumb_maker.txt")
    if not system_prompt:
        system_prompt = """Você é um Diretor de Arte Sênior de YouTube especializado em criar conceitos visuais para thumbnails de altíssimo CTR.
Você DEVE obrigatoriamente retornar a sua resposta EXCLUSIVAMENTE em um formato JSON válido, com a exata estrutura abaixo.
{
  "conflito_principal": "Uma frase resumindo o gatilho mental",
  "capas": [
    {
      "estrategia": "Nome da estratégia",
      "psicologia": "Breve explicação psicológica",
      "prompt_gringo": "Prompt hiper-detalhado em INGLÊS para Midjourney"
    }
  ]
}"""

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
        # BLINDAGEM DE JSON PARA O FRONTEND (CÓDIGO À PROVA DE FALHAS)
        # ==========================================
        dados_str = dados_str.strip()
        
        # Remove os blocos de formatação markdown do texto se a IA os enviar
        if "```json" in dados_str:
            dados_str = dados_str.split("```json")[1].split("```")[0]
        elif "```" in dados_str:
            dados_str = dados_str.split("```")[1].split("```")[0]
            
        dados_str = dados_str.strip()
        
        try:
            dados_json = json.loads(dados_str)
        except json.JSONDecodeError:
            raise Exception("A IA falhou em estruturar o arquivo visual. Tente gerar novamente.")

        # Trava de segurança absoluta: evita o erro .forEach no javascript
        if "capas" not in dados_json:
            dados_json["capas"] = []

        usuario.coins -= custo_operacao
        
        texto_historico = "🎨 THUMB MAKER - DIREÇÃO DE ARTE\n\n"
        texto_historico += f"🎯 CONFLITO PRINCIPAL: {dados_json.get('conflito_principal', '')}\n"
        texto_historico += "=" * 50 + "\n\n"
        
        for i, capa in enumerate(dados_json.get("capas", [])):
            texto_historico += f"🖼️ CONCEITO {i+1} ({capa.get('estrategia', '')})\n"
            texto_historico += f"🧠 Psicologia: {capa.get('psicologia', '')}\n"
            texto_historico += f"🪄 Prompt Midjourney:\n{capa.get('prompt_gringo', '')}\n"
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
