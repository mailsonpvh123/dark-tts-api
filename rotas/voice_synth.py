import edge_tts
import base64
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Voice Synthesizer"])

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

@router.get("/vozes")
async def listar_vozes():
    if vozes_cache:
        return {"status": "sucesso", "vozes": vozes_cache}
    else:
        return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

@router.post("/gerar_narracao")
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
        return {"status": "erro", "mensagem": str(e)}
