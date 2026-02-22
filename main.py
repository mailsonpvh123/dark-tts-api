from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importando nossas ferramentas modulares
from rotas import minerador, voice_synth, audio_mixer, gen_legends

app = FastAPI(
    title="Dark Creator API", 
    description="API Modular para o Dark Creator OS", 
    version="2.0"
)

# Configuração do CORS (MUITO IMPORTANTE para não dar erro no Front)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Se quiser, depois mude para o domínio do seu front-end
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Plugando as ferramentas no servidor principal
app.include_router(minerador.router)
app.include_router(voice_synth.router)
app.include_router(audio_mixer.router)
app.include_router(gen_legends.router)

@app.get("/")
def ping():
    return {"status": "Dark Creator OS Backend 100% Online e Modular"}
