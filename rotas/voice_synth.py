import edge_tts
import base64
import math
import os
import io
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pydub import AudioSegment

from google import genai
from google.genai import types

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(tags=["Voice Synthesizer"])

# Modelos atualizados com os parâmetros do Gemini
class AudioRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    volume: int = 0
    temperatura: float = 1.0       # Novo: Para o Gemini
    instrucao_estilo: str = ""     # Novo: Para o Gemini

# Mapa oficial das 21 Vozes Premium (Revisado com o Google AI Studio)
VOICES_MAP = {
    "Puck": "Animado / Jovem", "Charon": "Informativo / Grave", "Kore": "Firme / Madura",
    "Fenrir": "Excitado / Forte", "Leda": "Jovem / Articulada", "Orus": "Firme / Clássico",
    "Aoede": "Suave / Breezy", "Callirrhoe": "Relaxado", "Zephyr": "Brilhante / Enérgico",
    "Despina": "Suave", "Erinome": "Claro", "Algenib": "Áspero", 
    "Rasalgethi": "Informativo", "Laomedeia": "Animado", "Pulcherrima": "Avançado",
    "Achird": "Amigável", "Zubenelgenubi": "Casual", "Vindemiatrix": "Gentil",
    "Sadachbia": "Vivo", "Sadaltager": "Sábio", "Sulafat": "Caloroso"
}

vozes_cache = []

@router.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    vozes_cache.clear() # <- O SEGREDO ESTÁ AQUI: Limpa a lista para não duplicar no reload do Easypanel
    
    try:
        # 1. Carregando as 21 Vozes Premium (Gemini)
        for v_name, v_desc in VOICES_MAP.items():
            vozes_cache.append({
                "name": f"{v_name} ({v_desc})",
                "shortName": f"gemini-premium-{v_name}",
                "gender": "Neutral",
                "tipo": "premium"
            })
        
        # 2. Carregando as Vozes Padrão (Edge TTS)
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
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
        
    texto = req.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="O texto para narração é obrigatório.")

    is_premium = req.voz.startswith("gemini-premium")
    tamanho_texto = len(texto)

    # ==========================================
    # CÁLCULO DE CUSTO E TRAVAS DE SEGURANÇA
    # ==========================================
    if is_premium:
        if tamanho_texto > 4500:
            raise HTTPException(status_code=400, detail=f"Texto muito longo para Voz Premium (Máximo 4500). Você enviou {tamanho_texto} caracteres.")
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 10))
    else:
        custo_operacao = 30

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para esta narração.")

    usuario.coins -= custo_operacao
    db.commit()

    # ==========================================
    # GERAÇÃO DE ÁUDIO (HÍBRIDA)
    # ==========================================
    try:
        srt_content = ""
        audio_base64 = ""

        if is_premium:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key: raise ValueError("Chave GEMINI_API_KEY não configurada no Easypanel.")

            client = genai.Client(api_key=api_key)
            
            # Extrai o nome real da voz (ex: "gemini-premium-Aoede" -> "Aoede")
            voz_real = req.voz.split("-")[-1] 
            
            # Injeta o Prompt de Direção de Arte ou um padrão
            instrucao = req.instrucao_estilo if req.instrucao_estilo else "Você é um narrador profissional. Leia o texto com emoção adequada e ritmo perfeito."

            kwargs = {
                "response_modalities": ["AUDIO"],
                "system_instruction": instrucao,
                "temperature": req.temperatura,
                "speech_config": types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voz_real)
                    )
                )
            }
            
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=texto, 
                config=types.GenerateContentConfig(**kwargs)
            )
            
            pcm_data = next((part.inline_data.data for part in response.candidates[0].content.parts if part.inline_data), None)
            if not pcm_data: raise ValueError("A API do Gemini falhou em retornar o áudio.")

            # Conversão PyDub (Memória)
            seg = AudioSegment(data=pcm_data, sample_width=2, frame_rate=24000, channels=1)
            mp3_io = io.BytesIO()
            seg.export(mp3_io, format="mp3", bitrate="128k")
            audio_base64 = base64.b64encode(mp3_io.getvalue()).decode('utf-8')

        else:
            voz_engine = req.voz
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
        
        ferramenta_nome = "Voice Synth Premium" if is_premium else "Voice Synth"
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta=ferramenta_nome,
            input_usuario=f"Voz: {req.voz} | Texto: {texto[:100]}...",
            resultado="Áudio gerado com sucesso.", 
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content, "novo_saldo": usuario.coins}

    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro na Geração de Áudio: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na IA. Os seus {custo_operacao} coins foram estornados. Tente novamente.")
