from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import edge_tts
import nltk
from pydub import AudioSegment
import tempfile
import os
import base64
import asyncio
import uuid

app = FastAPI(title="Dark TTS API")

# Modelo de dados que a API vai receber do n8n
class TTSRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural"
    velocidade: int = 0
    pitch: int = 0
    volume: int = 0

def split_text_inteligentemente(texto, max_chars=1500):
    texto = texto.replace('*', '').replace('#', '').replace('"', '').replace('”', '').replace('“', '')
    try: sentences = nltk.sent_tokenize(texto, language='portuguese')
    except: sentences = [s.strip() for s in texto.replace('\n', ' ').split('.') if s.strip()]
        
    chunks = []; current_chunk = ""
    for s in sentences:
        s = s.strip()
        if not s: continue
        if len(current_chunk) + len(s) < max_chars: current_chunk += s + " "
        else:
            if current_chunk: chunks.append(current_chunk.strip())
            current_chunk = s + " "
    if current_chunk: chunks.append(current_chunk.strip())
    return chunks

async def gerar_audio_completo(req: TTSRequest):
    rate_str = f"+{req.velocidade}%" if req.velocidade >= 0 else f"{req.velocidade}%"
    pitch_str = f"+{req.pitch}Hz" if req.pitch >= 0 else f"{req.pitch}Hz"
    vol_str = f"+{req.volume}%" if req.volume >= 0 else f"{req.volume}%"

    chunks = split_text_inteligentemente(req.texto)
    arquivos_gerados = []
    
    timeline_lines = []
    current_ms = 0
    PAUSE_DURATION_MS = 250 

    for chunk in chunks:
        if not chunk.strip(): continue
        
        temp_mp3 = os.path.join(tempfile.gettempdir(), f"chunk_{uuid.uuid4()}.mp3")
        try:
            communicate = edge_tts.Communicate(chunk, req.voz, rate=rate_str, pitch=pitch_str, volume=vol_str)
            await communicate.save(temp_mp3)
            
            wav_path = temp_mp3.replace(".mp3", ".wav")
            segment = AudioSegment.from_file(temp_mp3)
            segment.export(wav_path, format="wav")
            arquivos_gerados.append(wav_path)
            
            # Timeline
            ts_sec = int(current_ms / 1000)
            m, s = divmod(ts_sec, 60)
            preview = chunk.replace('\n', ' ').strip()[:40]
            timeline_lines.append(f"{m:02d}:{s:02d} - {preview}...")
            
            current_ms += len(segment) + PAUSE_DURATION_MS
        except Exception as e:
            print(f"Erro no chunk: {e}")
        finally:
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)

    if not arquivos_gerados:
        raise Exception("Nenhum áudio pôde ser gerado.")

    # Unir áudios
    final_audio = AudioSegment.empty()
    pause = AudioSegment.silent(duration=PAUSE_DURATION_MS)
    
    for i, f in enumerate(arquivos_gerados):
        try: 
            final_audio += (pause + AudioSegment.from_wav(f)) if i > 0 else AudioSegment.from_wav(f)
        finally:
            if os.path.exists(f): os.remove(f)

    # Salvar temporariamente para codificar
    final_path = os.path.join(tempfile.gettempdir(), f"final_{uuid.uuid4()}.wav")
    final_audio.export(final_path, format="wav")

    # Converter o ficheiro de áudio para Base64 (Texto)
    with open(final_path, "rb") as audio_file:
        audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
    
    os.remove(final_path)

    timeline_texto = "\n".join(timeline_lines)
    
    return {
        "status": "sucesso",
        "audio_base64": audio_base64,
        "timeline": timeline_texto
    }

@app.post("/gerar_narracao")
async def api_gerar_narracao(req: TTSRequest):
    try:
        resultado = await gerar_audio_completo(req)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
