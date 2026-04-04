import os
import json
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

router = APIRouter(prefix="/api/v1", tags=["Gen Insights"])

# A MÁGICA CONTRA O ERRO 422 ESTÁ AQUI:
# Tornamos os campos flexíveis. Se o JS enviar 'publico' ou 'publico_alvo', o Python aceita e não crasha.
class InsightRequest(BaseModel):
    nicho: str
    publico_alvo: str = "" 
    publico: str = ""      

@router.post("/gen-insights")
async def process_insights(
    req: InsightRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.nicho:
        raise HTTPException(status_code=400, detail="O nicho é obrigatório.")

    # Consolida a variável, pegando a que vier preenchida do frontend
    publico_final = req.publico_alvo if req.publico_alvo else req.publico

    custo_operacao = 5

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins.")

    # Débito Antecipado
    usuario.coins -= custo_operacao
    db.commit()

    try:
        api_key = os.environ.get("GEMINI_API_KEY_FREE") or os.environ.get("GEMINI_API_KEY")
        modelo_texto = os.environ.get("GEMINI_MODEL_TEXT", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("Chave GEMINI_API_KEY_FREE não configurada.")

        client = genai.Client(api_key=api_key)

        system_prompt = """Você é um estrategista de conteúdo viral para YouTube (Canais Dark).
O usuário fornecerá um nicho e um público-alvo.
Sua missão é gerar 3 ideias de vídeos altamente virais.
VOCÊ DEVE RETORNAR EXATAMENTE UM JSON VÁLIDO COM A SEGUINTE ESTRUTURA:
{
  "ideias": [
    {
      "titulo": "Título clickbait e magnético",
      "gancho": "A frase exata dos primeiros 5 segundos do vídeo",
      "resumo": "Resumo de 3 linhas sobre o que o vídeo abordará"
    }
  ]
}
Não inclua marcações Markdown (```json) na resposta, apenas o JSON puro."""

        user_content = f"Nicho: {req.nicho}\nPúblico-Alvo: {publico_final}"

        print(f"🧠 Iniciando Gen Insights (Nicho: {req.nicho}). Custo: {custo_operacao} Coins.")

        # ==========================================
        # RETRY COM EXPONENTIAL BACKOFF (BLINDAGEM DE REDE)
        # ==========================================
        max_retries = 3
        dados_str = ""
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=modelo_texto,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.8 
                    )
                )
                dados_str = response.text.strip()
                break
            except Exception as e_api:
                err_msg = str(e_api).lower()
                if "503" in err_msg or "429" in err_msg or "unavailable" in err_msg or "demand" in err_msg:
                    if attempt < max_retries - 1:
                        espera = 2 * (2 ** attempt)
                        print(f"⚠️ Motor Ocupado (Gen Insights). A aguardar {espera}s... (Tentativa {attempt+1}/{max_retries})")
                        await asyncio.sleep(espera)
                    else:
                        raise Exception("A Dark Neural Engine está sob tráfego extremo. Tente novamente.")
                else:
                    raise e_api

        # Limpeza do JSON caso o motor insista no Markdown
        match = re.search(r'```json\s*(.*?)\s*```', dados_str, re.DOTALL)
        if match:
            dados_str = match.group(1)
        
        try:
            dados_json = json.loads(dados_str)
        except json.JSONDecodeError:
            raise Exception("A IA não retornou um formato de dados válido. Tente novamente.")

        ideias_geradas = dados_json.get("ideias", [])

        # Salva no Histórico para o usuário baixar depois
        texto_historico = "💡 GEN INSIGHTS - PAUTAS VIRAIS\n\n"
        for i, ideia in enumerate(ideias_geradas):
            texto_historico += f"🔥 TÍTULO {i+1}: {ideia.get('titulo')}\n"
            texto_historico += f"🎣 GANCHO: {ideia.get('gancho')}\n"
            texto_historico += f"📝 RESUMO: {ideia.get('resumo')}\n"
            texto_historico += "-" * 40 + "\n\n"

        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Gen Insights",
            input_usuario=f"Nicho: {req.nicho} | Público: {publico_final}",
            resultado=texto_historico.strip(), 
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {
            "status": "sucesso", 
            "ideias": ideias_geradas, 
            "novo_saldo": usuario.coins
        }

    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no Gen Insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))
