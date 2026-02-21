import edge_tts
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64

app = FastAPI()

# Configuração do CORS (A ponte de segurança entre o seu site e a API)
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

# --- SISTEMA DE CACHE DE VOZES ---
# Carrega as vozes na memória quando o servidor liga, evitando travamentos e bloqueios da Microsoft.
vozes_cache = []

@app.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    try:
        voices = await edge_tts.list_voices()
        for v in voices:
            # Filtra PT-BR e Multilingual e formata as chaves exatamente como o seu Site espera
            if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
                vozes_cache.append({
                    "name": v["Name"],
                    "shortName": v["ShortName"],
                    "gender": v["Gender"]
                })
        print(f"✅ {len(vozes_cache)} Vozes carregadas com sucesso na memória!")
    except Exception as e:
        print(f"Erro ao carregar vozes: {e}")

@app.get("/vozes")
async def listar_vozes():
    # O site agora recebe as vozes da memória em milissegundos
    if vozes_cache:
        return {"status": "sucesso", "vozes": vozes_cache}
    else:
        return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

@app.post("/gerar_narracao")
async def gerar_narracao(req: AudioRequest):
    try:
        # Formata a velocidade e o pitch para o padrão da API (+0%, +0Hz)
        velocidade_formatada = f"{int((req.velocidade - 1.0) * 100):+d}%"
        pitch_formatado = f"{req.pitch:+d}Hz"
        
        # Prepara o comunicador e o criador de legendas (SubMaker)
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
        
        # Gera o arquivo SRT completo
        srt_content = submaker.generate_subs()
        
        # Converte o áudio para base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "status": "sucesso",
            "audio_base64": audio_base64,
            "srt": srt_content
        }
        
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
