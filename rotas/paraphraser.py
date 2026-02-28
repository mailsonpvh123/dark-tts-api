import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# IMPORT DA SDK OFICIAL DO GEMINI
from google import genai
from google.genai import types

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1/paraphraser", tags=["Paraphraser"])

class ParaphraseRequest(BaseModel):
    texto: str
    tom: str = "Sarcástico e Ácido"
    idioma: str = "Português (Brasil)"

@router.post("/")
async def gerar_parafraze(
    req: ParaphraseRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
        
    texto_original = req.texto.strip()
    if not texto_original:
        raise HTTPException(status_code=400, detail="O texto original não pode estar vazio.")

    # Custo fixo para a ferramenta de reescrita
    custo_operacao = 15

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para reescrever.")

    # Débito antecipado
    usuario.coins -= custo_operacao
    db.commit()

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Chave GEMINI_API_KEY não configurada no servidor.")

        client = genai.Client(api_key=api_key)

        # Instrução de Sistema: Transforma a IA num Copywriter de Elite
        instrucao_sistema = (
            "Você é um roteirista de elite especializado em vídeos curtos (TikTok/Shorts) e longos para o YouTube. "
            "Sua missão é reescrever o texto fornecido garantindo 100% de originalidade para evitar qualquer detecção de plágio, "
            "mas mantendo a essência, os fatos e a informação do conteúdo original. "
            "Adapte o vocabulário para ser lido em voz alta de forma natural por um locutor (evite palavras robóticas ou excessivamente formais, a não ser que o tom exija)."
        )
        
        # O Prompt de comando do usuário
        prompt = (
            f"Reescreva o texto abaixo no idioma '{req.idioma}'.\n"
            f"Aplique estritamente um tom de voz: {req.tom}.\n\n"
            f"Texto original:\n{texto_original}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=instrucao_sistema,
                temperature=0.8 # 0.8 garante criatividade suficiente para fugir do plágio
            )
        )
        
        texto_gerado = response.text

        # Salva no histórico
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Paraphraser",
            input_usuario=f"Tom: {req.tom} | Idioma: {req.idioma}\nTexto original: {texto_original[:100]}...",
            resultado=texto_gerado[:150] + "...", 
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {
            "status": "sucesso", 
            "texto_parafrazedo": texto_gerado, 
            "novo_saldo": usuario.coins
        }

    except Exception as e:
        # ROLLBACK: Devolve o dinheiro se der erro
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no Paraphraser: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na Inteligência Artificial. Os seus {custo_operacao} coins foram estornados. Tente novamente.")
