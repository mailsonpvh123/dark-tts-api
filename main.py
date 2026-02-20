from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import edge_tts
import nltk
from pydub import AudioSegment
import tempfile
import os
import base64
import uuid

app = FastAPI(title="Dark TTS Master API")

# Libera o CORS na própria API para garantir que o site consegue puxar a lista de vozes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AVAILABLE_VOICES = []
VOICE_MAP = {}

@app.on_event("startup")
async def load_voices():
    try:
        vozes = await edge_tts.list_voices()
        lst = []
        for v in vozes:
            short = v.get('ShortName')
            full = v.get('Name')
            loc = v.get('Locale')
            if not short: continue
            
            try: disp = full.split('(')[-1].split(')')[0].split(',')[-1].strip()
            except: disp = short
            name = f"{disp} ({loc})"
            
            # --- O SEU FILTRO MÁGICO AQUI ---
            if "Multilingual" in disp or "Multilingual" in name:
                prio = 0
            elif loc == "pt-BR":
                prio = 1
            else:
                continue # IGNORA TUDO O RESTO DO MUNDO!
            
            VOICE_MAP[name] = short
            lst.append((prio, loc, name))
        
        lst.sort(key=lambda x: (x[0], x[1], x[2]))
        for item in lst:
            AVAILABLE_VOICES.append({"name": item[2], "shortName": VOICE_MAP[item[2]], "locale": item[1]})
        print(f"✅ {len(AVAILABLE_VOICES)} Vozes (Apenas Multi e PT-BR) carregadas!")
    except Exception as e:
        print(f"❌ Erro ao carregar vozes: {e}")

@app.get("/vozes")
async def listar_vozes():
    return {"vozes": AVAILABLE_VOICES}

class TTSRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural" 
    velocidade: float = 1.0  
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
    rate_val = int((req.velocidade - 1.0) * 100)
    rate_str = f"+{rate_val}%" if rate_val >= 0 else f"{rate_val}%"
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
            
            ts_sec = int(current_ms / 1000)
            m, s = divmod(ts_sec, 60)
            preview = chunk.replace('\n', ' ').strip()[:40]
            timeline_lines.append(f"{m:02d}:{s:02d} - {preview}...")
            
            current_ms += len(segment) + PAUSE_DURATION_MS
        except Exception as e:
            print(f"Erro no chunk: {e}")
        finally:
            if os.path.exists(temp_mp3): os.remove(temp_mp3)

    if not arquivos_gerados: raise Exception("Nenhum áudio pôde ser gerado.")

    final_audio = AudioSegment.empty()
    pause = AudioSegment.silent(duration=PAUSE_DURATION_MS)
    
    for i, f in enumerate(arquivos_gerados):
        try: final_audio += (pause + AudioSegment.from_wav(f)) if i > 0 else AudioSegment.from_wav(f)
        finally:
            if os.path.exists(f): os.remove(f)

    final_path = os.path.join(tempfile.gettempdir(), f"final_{uuid.uuid4()}.wav")
    final_audio.export(final_path, format="wav")

    with open(final_path, "rb") as audio_file:
        audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
    os.remove(final_path)

    timeline_texto = "\n".join(timeline_lines)
    return {"status": "sucesso", "audio_base64": audio_base64, "timeline": timeline_texto}

@app.post("/gerar_narracao")
async def api_gerar_narracao(req: TTSRequest):
    try:
        return await gerar_audio_completo(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
