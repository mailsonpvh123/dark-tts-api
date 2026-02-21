import edge_tts
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64

app = FastAPI()

# Configuração do CORS (Para o seu site conseguir conversar com a API)
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

@app.get("/vozes")
async def listar_vozes():
    try:
        voices = await edge_tts.list_voices()
        vozes_pt = [v for v in voices if v["Locale"].startswith("pt-")]
        return {"status": "sucesso", "vozes": vozes_pt}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

@app.post("/gerar_narracao")
async def gerar_narracao(req: AudioRequest):
    try:
        # Formata a velocidade e o pitch
        velocidade_formatada = f"{int((req.velocidade - 1.0) * 100):+d}%"
        pitch_formatado = f"{req.pitch:+d}Hz"
        
        # Prepara o comunicador e o criador de legendas
        communicate = edge_tts.Communicate(
            text=req.texto, 
            voice=req.voz, 
            rate=velocidade_formatada, 
            pitch=pitch_formatado
        )
        submaker = edge_tts.SubMaker()
        
        audio_data = bytearray()
        
        # Inicia o streaming para capturar Áudio e os Tempos (WordBoundary)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
        
        # Gera o arquivo SRT em texto
        srt_content = submaker.generate_subs()
        
        # Converte o áudio para base64 para mandar pro site
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "status": "sucesso",
            "audio_base64": audio_base64,
            "srt": srt_content
        }
        
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
