import edge_tts
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import uvicorn
import os
import re
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AudioRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    volume: int = 0

class YoutubeRequest(BaseModel):
    url: str

vozes_cache = []

@app.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    try:
        voices = await edge_tts.list_voices()
        for v in voices:
            if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
                vozes_cache.append({
                    "name": v["Name"],
                    "shortName": v["ShortName"],
                    "gender": v["Gender"]
                })
        print(f"✅ {len(vozes_cache)} Vozes carregadas com sucesso na memória!")
    except Exception as e:
        print(f"❌ Erro ao carregar vozes: {e}")

@app.get("/vozes")
async def listar_vozes():
    if vozes_cache:
        return {"status": "sucesso", "vozes": vozes_cache}
    else:
        return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

# ==========================================
# NOVO MOTOR: EXTRATOR DE LEGENDAS YOUTUBE
# ==========================================
@app.post("/extrair_youtube")
async def extrair_youtube(req: YoutubeRequest):
    try:
        # Pega o ID do video do link sujo
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", req.url)
        if not match:
            return {"status": "erro", "mensagem": "Link do YouTube inválido."}
        
        video_id = match.group(1)

        # Baixa as legendas (tenta achar qualquer idioma disponível)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['pt', 'pt-BR', 'en', 'es'])
        except:
            transcript = transcript_list.find_transcript([t.language_code for t in transcript_list])

        # Junta tudo num textão limpo
        texto_completo = " ".join([t['text'] for t in transcript.fetch()])
        
        return {"status": "sucesso", "texto": texto_completo}
    except Exception as e:
        return {"status": "erro", "mensagem": f"Não foi possível extrair a legenda. O vídeo pode não ter legendas ocultas. Erro: {str(e)}"}

# ==========================================
# MOTOR DE VOZ
# ==========================================
@app.post("/gerar_narracao")
async def gerar_narracao(req: AudioRequest):
    try:
        velocidade_formatada = f"{int((req.velocidade - 1.0) * 100):+d}%"
        pitch_formatado = f"{req.pitch:+d}Hz"
        
        communicate = edge_tts.Communicate(text=req.texto, voice=req.voz, rate=velocidade_formatada, pitch=pitch_formatado)
        submaker = edge_tts.SubMaker()
        audio_data = bytearray()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
        
        srt_content = submaker.get_srt()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content}
        
    except Exception as e:
        print(f"❌ Erro na geração de áudio: {e}")
        return {"status": "erro", "mensagem": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
