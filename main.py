import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Importa as rotas dos nossos arquivos modulares
from rotas import minerador, voice_synth, audio_mixer, paraphraser, gen_insights, script_forge, meta_seo
#from rotas import gen_legends

app = FastAPI(
    title="Dark Creator OS - API",
    description="SaaS Full-Stack para Criação de Canais Dark.",
    version="2.2"
)

# --- CONFIGURAÇÃO DE FRONT-END ---
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
#app.include_router(gen_legends.router)
app.include_router(paraphraser.router)
app.include_router(gen_insights.router)
app.include_router(script_forge.router)
app.include_router(meta_seo.router)

# --- ROTAS VISUAIS (NAVEGAÇÃO DO USUÁRIO) ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página Inicial / Dashboard"""
    return templates.TemplateResponse("base.html", {"request": request, "title": "Dashboard"})

@app.get("/gen-insights", response_class=HTMLResponse)
async def gen_insights_page(request: Request):
    return templates.TemplateResponse("gen_insights.html", {"request": request, "title": "Gen Insights"})

@app.get("/paraphraser", response_class=HTMLResponse)
async def paraphraser_page(request: Request):
    return templates.TemplateResponse("paraphraser.html", {"request": request, "title": "Text Transmuter"})

@app.get("/script-forge", response_class=HTMLResponse)
async def script_forge_page(request: Request):
    return templates.TemplateResponse("script_forge.html", {"request": request, "title": "Script Forge"})

@app.get("/voice-synthesizer", response_class=HTMLResponse)
async def voice_synthesizer_page(request: Request):
    return templates.TemplateResponse("voice_synthesizer.html", {"request": request, "title": "Voice Synthesizer"})

# Adicionando rotas para as páginas que ainda estão no n8n (caso você já as tenha criado no GitHub)
@app.get("/miner", response_class=HTMLResponse)
async def miner_page(request: Request):
    return templates.TemplateResponse("miner.html", {"request": request, "title": "Miner"})

@app.get("/audio-mixer", response_class=HTMLResponse)
async def mixer_page(request: Request):
    return templates.TemplateResponse("audio_mixer.html", {"request": request, "title": "Audio Mixer"})

@app.get("/meta-seo", response_class=HTMLResponse)
async def seo_page(request: Request):
    return templates.TemplateResponse("meta_seo.html", {"request": request, "title": "Meta & SEO"})

@app.get("/thumb-maker", response_class=HTMLResponse)
async def thumb_page(request: Request):
    return templates.TemplateResponse("thumb_maker.html", {"request": request, "title": "Thumb Maker"})

@app.get("/gen-legends", response_class=HTMLResponse)
async def legends_page(request: Request):
    return templates.TemplateResponse("gen_legends.html", {"request": request, "title": "Gen Legends"})

# --- ROTA DE STATUS ---
@app.get("/api/status")
def check_status():
    return {"status": "online", "message": "Motores neurais rodando liso!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
