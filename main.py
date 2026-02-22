from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa as rotas dos arquivos modulares que criamos
from rotas import minerador, voice_synth, audio_mixer, gen_legends

# Inicializa o app FastAPI
app = FastAPI(
    title="Dark Creator OS - API",
    description="Motores neurais separados de forma modular.",
    version="2.0"
)

# Configuração de CORS (Essencial para seu HTML conversar com a API sem bloqueios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite qualquer origem
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Acoplando as ferramentas no motor principal
app.include_router(minerador.router)
app.include_router(voice_synth.router)
app.include_router(audio_mixer.router)
app.include_router(gen_legends.router)

# Rota de Status / Ping
@app.get("/")
def check_status():
    return {"status": "online", "message": "Servidor do Dark Creator está rodando liso e modular!"}
