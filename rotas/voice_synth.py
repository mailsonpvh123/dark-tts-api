import edge_tts
import base64
import math
import os
import io
import time
import re
import textwrap
import httpx 
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pydub import AudioSegment

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(tags=["Voice Synthesizer"])

class AudioRequest(BaseModel):
    texto: str
    voz: str = "padrao-pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0

# ==========================================
# CATÁLOGOS DE VOZES (SEM CITAR MOTORES NA API)
# ==========================================
# O Novo Elenco Creator (Gemini Flash TTS)
VOICES_CREATOR = {
    "Aoede": "Feminino / Acolhedora e Natural",
    "Charon": "Masculino / Denso e Sombrio (Ideal p/ Dark e Suspense)",
    "Fenrir": "Masculino / Intenso e Envolvente",
    "Kore": "Feminino / Clara e Energética",
    "Puck": "Andrógino / Versátil e Sarcástico"
}

# O Elenco de Elite Completo (21 Vozes Nativas ElevenLabs)
VOICES_CINEMATIC = {
    "pNInz6obpgDQGcFmaJgB": {"nome": "Adam", "desc": "Dominante e Firme"},
    "Xb7hH8MSUJpSbSDYk0k2": {"nome": "Alice", "desc": "Clara, Educadora Envolvente"},
    "hpp4J3VqNfWAUOO0d1Us": {"nome": "Bella", "desc": "Profissional, Vibrante e Acolhedora"},
    "pqHfZKP75CvOlQylNhV4": {"nome": "Bill", "desc": "Sábio, Maduro e Equilibrado"},
    "nPczCjzI2devNBz1zQrb": {"nome": "Brian", "desc": "Profundo, Ressonante e Confortante"},
    "N2lVS1w4EtoT3dr4eOWO": {"nome": "Callum", "desc": "Rouco, Irreverente e Cativante"},
    "IKne3meq5aSn9XLyUdCD": {"nome": "Charlie", "desc": "Profundo, Confiante e Energético"},
    "iP95p4xoKVk53GoZ742B": {"nome": "Chris", "desc": "Charmoso e Pé no Chão"},
    "onwK4e9ZLuTAKqWW03F9": {"nome": "Daniel", "desc": "Locutor Estável e Seguro"},
    "cjVigY5qzO86Huf0OWal": {"nome": "Eric", "desc": "Suave e Confiável"},
    "JBFqnCBsd6RMkjVDRZzb": {"nome": "George", "desc": "Acolhedor, Narrador Cativante"},
    "SOYHLrjzK2X1ezoPC6cr": {"nome": "Harry", "desc": "Intenso e Feroz (Narrativa Épica)"},
    "cgSgspJ2msm6clMCkdW9": {"nome": "Jessica", "desc": "Divertida, Vibrante e Acolhedora"},
    "FGY2WhTYpPnrIDTdsKH5": {"nome": "Laura", "desc": "Entusiasta e Cheia de Atitude"},
    "TX3LPaxmHKxFdv7VOQHJ": {"nome": "Liam", "desc": "Energético (Criador de Conteúdo)"},
    "pFZP5JQG7iQjIQuC4Bku": {"nome": "Lily", "desc": "Voz Aveludada e Teatral"},
    "XrExE9yKIg1WjnnlVkGX": {"nome": "Matilda", "desc": "Profissional e Culta"},
    "SAz9YHcvj6GT2YYXdXww": {"nome": "River", "desc": "Relaxado, Neutro e Informativo"},
    "CwhRBWXzGAHq8TQ4Fs17": {"nome": "Roger", "desc": "Descontraído, Casual e Ressonante"},
    "EXAVITQu4vr4xnSDxMaL": {"nome": "Sarah", "desc": "Madura, Tranquilizadora e Confiante"},
    "bIHbv24MWmeRgasZH58o": {"nome": "Will", "desc": "Otimista e Relaxado"}
}

vozes_cache = []

@router.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    vozes_cache.clear() 
    
    try:
        # 1. Carrega Cinematic (Elite)
        for v_id, info in VOICES_CINEMATIC.items():
            vozes_cache.append({
                "name": f"{info['nome']} ({info['desc']})",
                "shortName": f"cinematic-{v_id}",
                "gender": "Neutral",
                "tipo": "cinematic"
            })

        # 2. Carrega Creator (Premium)
        for v_name, v_desc in VOICES_CREATOR.items():
            vozes_cache.append({
                "name": f"{v_name} ({v_desc})",
                "shortName": f"creator-{v_name}",
                "gender": "Neutral",
                "tipo": "creator"
            })
        
        # 3. Carrega Standard (Padrão)
        voices = await edge_tts.list_voices()
        for v in voices:
            if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
                vozes_cache.append({
                    "name": v["Name"],
                    "shortName": f"padrao-{v['ShortName']}",
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
    return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

# ==========================================
# O CHUNKER UNIVERSAL (4000 chars)
# ==========================================
def split_text_for_api(texto, max_chars=4000):
    texto = texto.replace('\n', ' ')
    frases = re.split(r'(?<=[.!?]) +', texto)
    chunks = []
    chunk_atual = ""
    for frase in frases:
        frase = frase.strip()
        if not frase: continue
        if len(chunk_atual) + len(frase) < max_chars:
            chunk_atual += frase + " "
        else:
            if chunk_atual: chunks.append(chunk_atual.strip())
            if len(frase) >= max_chars:
                pedacos = textwrap.wrap(frase, width=max_chars)
                for p in pedacos[:-1]: chunks.append(p.strip())
                chunk_atual = pedacos[-1] + " "
            else:
                chunk_atual = frase + " "
    if chunk_atual: chunks.append(chunk_atual.strip())
    return chunks

# ==========================================
# ROTA PRINCIPAL DE GERAÇÃO
# ==========================================
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

    # MODO FANTASMA (Previews)
    is_preview = texto.startswith("Olá, sou uma voz neural da sua plataforma.")
    
    # Roteamento Inteligente
    is_cinematic = req.voz.startswith("cinematic-")
    is_creator = req.voz.startswith("creator-")
    is_padrao = req.voz.startswith("padrao-")
    
    tamanho_texto = len(texto)

    # PRECIFICAÇÃO DE CEO
    if is_preview:
        custo_operacao = 0
    elif is_cinematic:
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 50))
    elif is_creator:
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 12))
    else:
        custo_operacao = 30 # Standard fixo

    if not is_preview:
        if usuario.coins < custo_operacao:
            raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins.")
        usuario.coins -= custo_operacao
        db.commit()

    try:
        srt_content = ""
        audio_base64 = ""
        
        chunks = split_text_for_api(texto, max_chars=4000)
        final_audio = AudioSegment.empty()
        pause_seg = AudioSegment.silent(duration=300)

        if is_cinematic:
            # === MOTOR 3: CINEMATIC (ELEVENLABS) ===
            api_key = os.environ.get("ELEVENLABS_API_KEY")
            modelo_eleven = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
            
            if not api_key: raise ValueError("Chave ELEVENLABS_API_KEY não configurada no Easypanel.")
            
            voz_real = req.voz.replace("cinematic-", "")
            print(f"🎬 Iniciando Dublagem Cinematic (Modelo: {modelo_eleven} | Voz ID: {voz_real} | Partes: {len(chunks)})")

            async with httpx.AsyncClient(timeout=120.0) as client:
                for i, chunk in enumerate(chunks):
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voz_real}"
                    headers = {
                        "xi-api-key": api_key,
                        "Content-Type": "application/json"
                    }
                    data = {
                        "text": chunk,
                        "model_id": modelo_eleven,
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    }
                    
                    response = await client.post(url, json=data, headers=headers)
                    if response.status_code != 200:
                        raise Exception(f"Falha na API Cinematic: {response.text}")
                    
                    seg = AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
                    final_audio += (pause_seg + seg) if i > 0 else seg

            mp3_io = io.BytesIO()
            final_audio.export(mp3_io, format="mp3", bitrate="128k")
            audio_base64 = base64.b64encode(mp3_io.getvalue()).decode('utf-8')

        elif is_creator:
            # === MOTOR 2: CREATOR (GEMINI TTS) ===
            api_key = os.environ.get("GEMINI_API_KEY_PAID")
            modelo_gemini = os.environ.get("GEMINI_MODEL_VOICE", "gemini-2.5-flash")
            
            if not api_key: raise ValueError("Chave GEMINI_API_KEY_PAID não configurada no Easypanel.")

            voz_real = req.voz.replace("creator-", "")
            print(f"🎙️ Iniciando Síntese Creator (Motor: {modelo_gemini} | Voz: {voz_real})")

            async with httpx.AsyncClient(timeout=120.0) as client:
                for i, chunk in enumerate(chunks):
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_gemini}:generateContent?key={api_key}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "contents": [{"parts": [{"text": chunk}]}],
                        "generationConfig": {
                            "responseModalities": ["AUDIO"],
                            "speechConfig": {
                                "voiceConfig": {
                                    "prebuiltVoiceConfig": {"voiceName": voz_real}
                                }
                            }
                        }
                    }
                    
                    max_retries = 3
                    audio_b64 = None
                    for attempt in range(max_retries):
                        try:
                            response = await client.post(url, json=data, headers=headers)
                            if response.status_code != 200:
                                raise Exception(response.text)
                            
                            resp_json = response.json()
                            for part in resp_json.get('candidates', [{}])[0].get('content', {}).get('parts', []):
                                if 'inlineData' in part and part['inlineData']['mimeType'].startswith('audio/'):
                                    audio_b64 = part['inlineData']['data']
                                    break
                                    
                            if audio_b64:
                                break
                            else:
                                raise Exception("A API do Gemini não retornou dados de áudio.")
                                
                        except Exception as api_err:
                            if attempt < max_retries - 1: time.sleep(3)
                            else: raise Exception(f"Falha na API Creator (Gemini): {str(api_err)}")
                    
                    audio_bytes = base64.b64decode(audio_b64)
                    seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
                    final_audio += (pause_seg + seg) if i > 0 else seg

            mp3_io = io.BytesIO()
            final_audio.export(mp3_io, format="mp3", bitrate="128k")
            audio_base64 = base64.b64encode(mp3_io.getvalue()).decode('utf-8')

        else:
            # === MOTOR 1: STANDARD (EDGE TTS) ===
            voz_engine = req.voz.replace("padrao-", "") 
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
        
        # SALVA NO DISCO
        if not is_preview:
            pasta_audios = os.path.join("frontend", "static", "audios", "historico")
            os.makedirs(pasta_audios, exist_ok=True)
            nome_arquivo = f"audio_{usuario.id}_{int(time.time())}.mp3"
            caminho_completo = os.path.join(pasta_audios, nome_arquivo)
            
            with open(caminho_completo, "wb") as f:
                f.write(base64.b64decode(audio_base64))
                
            ferramenta_nome = "Voice Synth - Cinematic" if is_cinematic else ("Voice Synth - Creator" if is_creator else "Voice Synth - Standard")
            novo_historico = models.Historico(
                usuario_id=usuario.id,
                ferramenta=ferramenta_nome,
                input_usuario=f"Voz: {req.voz} | Tamanho: {tamanho_texto} chars",
                resultado=f"/static/audios/historico/{nome_arquivo}",
                custo_coins=custo_operacao
            )
            db.add(novo_historico)
            db.commit()

        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content, "novo_saldo": usuario.coins}

    except Exception as e:
        if not is_preview:
            usuario.coins += custo_operacao
            db.commit()
        print(f"❌ Erro na Geração de Áudio: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar o áudio: {str(e)}")
