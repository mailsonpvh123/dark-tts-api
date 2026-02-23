import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Importa as rotas dos nossos arquivos modulares
from rotas import minerador, voice_synth, audio_mixer, gen_legends, paraphraser

# Inicializa o app FastAPI
app = FastAPI(
    title="Dark Creator OS - API",
    description="SaaS Full-Stack para Criação de Canais Dark.",
    version="2.1"
)

# --- CONFIGURAÇÃO DE FRONT-END ---

# 1. Monta a pasta de arquivos estáticos (CSS, JS)
# O diretório no servidor deve ser "frontend/static"
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# 2. Configura o diretório de templates do Jinja2
templates = Jinja2Templates(directory="frontend/templates")

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ACOPLANDO AS ROTAS DE API ---
app.include_router(minerador.router)
app.include_router(voice_synth.router)
app.include_router(audio_mixer.router)
app.include_router(gen_legends.router)
app.include_router(paraphraser.router)

# --- ROTAS DE PÁGINAS (FRONT-END) ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renderiza a página principal do Dashboard"""
    return templates.TemplateResponse("base.html", {
        "request": request, 
        "title": "Home"
    })

@app.get("/paraphraser", response_class=HTMLResponse)
async def paraphraser_page(request: Request):
    """Renderiza a página específica do Paraphraser"""
    return templates.TemplateResponse("paraphraser.html", {
        "request": request, 
        "title": "Text Transmuter"
    })

# Rota de Status da API
@app.get("/api/status")
def check_status():
    return {"status": "online", "message": "Motores neurais rodando liso!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # reload=True é ótimo para desenvolvimento, desative em produção
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
