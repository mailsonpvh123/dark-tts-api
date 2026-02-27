import edge_tts
import base64
import math
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import google.generativeai as genai
import os

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(tags=["Voice Synthesizer"])

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ AVISO: GEMINI_API_KEY não encontrada nas variáveis de ambiente!")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Modelos
class AudioRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    volume: int = 0

# Cache de vozes
vozes_cache = []

@router.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    try:
        # --- 1. INJETANDO A VOZ PREMIUM DE TESTE NA VITRINE ---
        vozes_cache.append({
            "name": "Gemini 2.5 Flash (Ultra-Realista)",
            "shortName": "gemini-premium-pt",
            "gender": "Neutral",
            "tipo": "premium"
        })
        
        # --- 2. CARREGANDO AS VOZES PADRÃO (EDGE TTS) ---
        voices = await edge_tts.list_voices()
        for v in voices:
            if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
                vozes_cache.append({
                    "name": v["Name"],
                    "shortName": v["ShortName"],
                    "gender": v["Gender"],
                    "tipo": "padrao"
                })
        print(f"✅ {len(vozes_cache)} Vozes carregadas com sucesso na memória!")
    except Exception as e:
        print(f"❌ Erro ao carregar vozes: {e}")

@router.get("/vozes")
async def listar_vozes():
    if vozes_cache:
        return {"status": "sucesso", "vozes": vozes_cache}
    else:
        return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

@router.post("/gerar_narracao")
async def gerar_narracao(
    req: AudioRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    # 1. VALIDAÇÃO BASE
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    texto = req.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="O texto para narração é obrigatório.")

    # ==========================================
    # 2. MOTOR DE PRECIFICAÇÃO E LIMITES (BACK-END)
    # ==========================================
    is_premium = req.voz.startswith("gemini-premium")
    tamanho_texto = len(texto)

    if is_premium:
        # Trava de Segurança contra Gargalo de API/Timeout
        if tamanho_texto > 4500:
            raise HTTPException(status_code=400, detail=f"Texto muito longo para Voz Premium (Máximo 4500). Você enviou {tamanho_texto} caracteres.")
        
        # Matemática: (Caracteres / 900) * 10 (Arredondado para cima. Mínimo 1)
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 10))
    else:
        # Preço fixo da voz padrão
        custo_operacao = 30

    # 3. VALIDAÇÃO DE SALDO E DÉBITO ANTECIPADO (Prevenção de fraude)
    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para esta narração.")

    usuario.coins -= custo_operacao
    db.commit()

    # ==========================================
    # 4. GERAÇÃO DE ÁUDIO COM SISTEMA DE ESTORNO
    # ==========================================
    try:
        # ATENÇÃO: Enquanto não plugamos a API real do Gemini, usamos uma voz Edge como "dublê" no motor
        voz_engine = "pt-BR-AntonioNeural" if is_premium else req.voz
        
        velocidade_formatada = f"{int((req.velocidade - 1.0) * 100):+d}%"
        pitch_formatado = f"{req.pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(text=texto, voice=voz_engine, rate=velocidade_formatada, pitch=pitch_formatado)
        submaker = edge_tts.SubMaker()
        audio_data = bytearray()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
        
        srt_content = submaker.get_srt()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # 5. SALVAR HISTÓRICO APÓS SUCESSO
        ferramenta_nome = "Voice Synth Premium" if is_premium else "Voice Synth"
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta=ferramenta_nome,
            input_usuario=f"Voz: {req.voz} | Vel: {req.velocidade}x | Pitch: {req.pitch}Hz\nTexto: {texto[:150]}...",
            resultado="Áudio e SRT gerados com sucesso.", 
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content, "novo_saldo": usuario.coins}

    except Exception as e:
        # 6. ROLLBACK: DEVOLVE O DINHEIRO SE A IA FALHAR
        usuario.coins += custo_operacao
        db.commit()
        raise HTTPException(status_code=500, detail=f"Falha na IA. Os seus {custo_operacao} coins foram estornados. Tente novamente.")
