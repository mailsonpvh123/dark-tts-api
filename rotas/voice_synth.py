import edge_tts
import base64
import math
import os
import io
import time
import re
import textwrap
import httpx # Para a chamada da ElevenLabs
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pydub import AudioSegment

import openai

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
# CATÁLOGOS DE VOZES (SEM CITAR MOTORES)
# ==========================================
VOICES_CREATOR = {
    "alloy": "Andrógino / Versátil",
    "echo": "Masculino / Suave",
    "fable": "Masculino / Expressivo",
    "onyx": "Masculino / Grave e Sombrio (Ideal p/ Dark)",
    "nova": "Feminino / Clara e Energética",
    "shimmer": "Feminino / Acolhedora",
    "ash": "Masculino / Quente e Conversacional",
    "coral": "Feminino / Vibrante e Polida",
    "sage": "Andrógino / Calmo e Reflexivo"
}

VOICES_CINEMATIC = {
    "pNInz6obpgDQGcFmaJgB": {"nome": "Adam", "desc": "Profundo e Narrativo (Documentários)"},
    "21m00Tcm4TlvDq8ikWAM": {"nome": "Rachel", "desc": "Calma e Conversacional"},
    "ErXwobaYiN019PkySvjV": {"nome": "Antony", "desc": "Firme e Confiante"},
    "EXAVITQu4vr4xnSDxMaL": {"nome": "Bella", "desc": "Suave e Envolvente"},
    "D38z5RcWu1voky8WS1ja": {"nome": "Fin", "desc": "Dinâmico e Expressivo"},
    "TxGEqnHWrfWFTfGW9XjX": {"nome": "Josh", "desc": "Grave e Dramático"},
    "MF3mGyEYCl7XYWbV9V6O": {"nome": "Elli", "desc": "Jovem e Emotiva"}
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
                "name": f"{v_name.capitalize()} ({v_desc})",
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
            # === MOTOR 2: CREATOR (OPENAI TTS ESTÁVEL) ===
            api_key = os.environ.get("OPENAI_API_KEY")
            # Agora recomendamos usar tts-1 ou tts-1-hd
            modelo_tts = os.environ.get("OPENAI_MODEL_TTS", "tts-1") 
            if not api_key: raise ValueError("Chave OPENAI_API_KEY não configurada no Easypanel.")

            client = openai.AsyncOpenAI(api_key=api_key)
            voz_real = req.voz.replace("creator-", "")
            
            print(f"🎙️ Iniciando Síntese Creator Estável (Modelo: {modelo_tts} | Voz: {voz_real})")

            for i, chunk in enumerate(chunks):
                max_retries = 3
                audio_bytes = None
                for attempt in range(max_retries):
                    try:
                        response = await client.audio.speech.create(
                            model=modelo_tts,
                            voice=voz_real,
                            input=chunk
                        )
                        audio_bytes = response.read()
                        break 
                    except Exception as api_err:
                        if attempt < max_retries - 1: time.sleep(3)
                        else: raise Exception(f"Falha na API Creator: {str(api_err)}")
                
                seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
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
            pasta_audios = os.path.join("frontend", "static", "audios")
            os.makedirs(pasta_audios, exist_ok=True)
            nome_arquivo = f"audio_{usuario.id}_{int(time.time())}.mp3"
            caminho_completo = os.path.join(pasta_audios, nome_arquivo)
            
            with open(caminho_completo, "wb") as f:
                f.write(base64.b64decode(audio_base64))
                
            ferramenta_nome = "Voz Cinematic" if is_cinematic else ("Voz Creator" if is_creator else "Voz Standard")
            novo_historico = models.Historico(
                usuario_id=usuario.id,
                ferramenta=ferramenta_nome,
                input_usuario=f"Voz: {req.voz} | Tamanho: {tamanho_texto} chars",
                resultado=f"/static/audios/{nome_arquivo}",
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
