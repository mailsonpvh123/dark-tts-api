import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Importa as rotas dos nossos arquivos modulares
from rotas import minerador, voice_synth, audio_mixer, gen_legends, paraphraser, gen_insights, script_forge

# Inicializa o app FastAPI
app = FastAPI(
    title="Dark Creator OS - API",
    description="SaaS Full-Stack para Criação de Canais Dark.",
    version="2.1"
)

# --- CONFIGURAÇÃO DE FRONT-END (HTML/CSS/JS) ---
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# --- MIDDLEWARE (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ACOPLANDO AS ROTAS DE API (BACK-END) ---
app.include_router(minerador.router)
app.include_router(voice_synth.router)
app.include_router(audio_mixer.router)
app.include_router(gen_legends.router)
app.include_router(paraphraser.router)
app.include_router(gen_insights.router)
app.include_router(script_forge.router) # <--- API do Script Forge acoplada aqui

# --- ROTAS VISUAIS (PÁGINAS DO SISTEMA) ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renderiza a página principal"""
    return templates.TemplateResponse("base.html", {
        "request": request, 
        "title": "Home"
    })

@app.get("/paraphraser", response_class=HTMLResponse)
async def paraphraser_page(request: Request):
    """Renderiza a página visual do Paraphraser"""
    return templates.TemplateResponse("paraphraser.html", {
        "request": request, 
        "title": "Text Transmuter"
    })

@app.get("/gen-insights", response_class=HTMLResponse)
async def gen_insights_page(request: Request):
    """Renderiza a página visual do Gen Insights"""
    return templates.TemplateResponse("gen_insights.html", {
        "request": request, 
        "title": "Gen Insights"
    })

@app.get("/script-forge", response_class=HTMLResponse)
async def script_forge_page(request: Request):
    """Renderiza a página visual do Script Forge"""
    return templates.TemplateResponse("script_forge.html", {
        "request": request, 
        "title": "Script Forge"
    })

# --- ROTA DE STATUS DA API ---
@app.get("/api/status")
def check_status():
    return {"status": "online", "message": "Motores neurais rodando liso!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # reload=False é o recomendado para produção no Easypanel
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
