import edge_tts
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import uvicorn
import os

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

@app.get("/vozes")
async def listar_vozes():
    try:
        voices = await edge_tts.list_voices()
        # Filtra apenas as vozes em Português do Brasil para a interface
        vozes_pt = [v for v in voices if v["Locale"].startswith("pt-")]
        return {"status": "sucesso", "vozes": vozes_pt}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

@app.post("/gerar_narracao")
async def gerar_narracao(req: AudioRequest):
    try:
        # 1. Formata a velocidade e o pitch para o padrão da API Microsoft (+0%, +0Hz)
        velocidade_formatada = f"{int((req.velocidade - 1.0) * 100):+d}%"
        pitch_formatado = f"{req.pitch:+d}Hz"
        
        # 2. Prepara o comunicador e o criador de legendas (O nosso extrator de Timeline!)
        communicate = edge_tts.Communicate(
            text=req.texto, 
            voice=req.voz, 
            rate=velocidade_formatada, 
            pitch=pitch_formatado
        )
        submaker = edge_tts.SubMaker()
        
        # 3. Variável de memória para guardar os bits do áudio
        audio_data = bytearray()
        
        # 4. Inicia o streaming (Captura o áudio e mapeia a palavra no exato milissegundo)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
        
        # 5. Gera o arquivo SRT completo e finalizado
        srt_content = submaker.generate_subs()
        
        # 6. Converte o áudio para base64 para enviar ao Front-end sem perder qualidade
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "status": "sucesso",
            "audio_base64": audio_base64,
            "srt": srt_content
        }
        
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

# O CORAÇÃO DO SERVIDOR (Esta é a parte que mantém o Easypanel acordado e ouvindo)
if __name__ == "__main__":
    # Pega a porta dinâmica do ambiente ou usa a 8000 como padrão
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
