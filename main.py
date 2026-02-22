import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa as rotas dos nossos arquivos modulares
from rotas import minerador, voice_synth, audio_mixer, gen_legends

# Inicializa o app FastAPI
app = FastAPI(
    title="Dark Creator OS - API",
    description="Motores neurais separados de forma modular.",
    version="2.0"
)

# Configuração de CORS para o front-end HTML conversar com a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Acoplando as ferramentas no motor principal
app.include_router(minerador.router)
app.include_router(voice_synth.router)
app.include_router(audio_mixer.router)
app.include_router(gen_legends.router)

# Rota de Status 
@app.get("/")
def check_status():
    return {"status": "online", "message": "Servidor do Dark Creator rodando liso e modular!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
