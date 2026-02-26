import uvicorn
import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# --- IMPORTS DO SISTEMA ---
import models
from database import engine, get_db
from auth import criar_token_acesso, verificar_senha, get_usuario_atual # Adicionamos get_usuario_atual aqui

# Importa as rotas dos arquivos modulares
from rotas import minerador, voice_synth, audio_mixer, paraphraser, gen_insights, script_forge, meta_seo, thumb_maker

# --- INICIALIZAÇÃO ---
app = FastAPI(
    title="Dark Creator OS - API",
    description="SaaS Full-Stack para Criação de Canais Dark.",
    version="3.0"
)

# Cria as tabelas no volume /app/data
models.Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

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
app.include_router(paraphraser.router)
app.include_router(gen_insights.router)
app.include_router(script_forge.router)
app.include_router(meta_seo.router)
app.include_router(thumb_maker.router)

# --- ROTA DE LOGIN ---
@app.post("/api/login")
async def login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    email = data.get("email")
    senha = data.get("password")

    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    
    if not usuario or not verificar_senha(senha, usuario.senha):
        return JSONResponse(status_code=401, content={"status": "erro", "message": "E-mail ou senha incorretos"})

    token = criar_token_acesso(data={"sub": usuario.email})
    
    response = JSONResponse(content={"status": "sucesso", "message": "Logado com sucesso!"})
    # O cookie mantém a sessão ativa no navegador
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=60*60*24*7)
    return response

# --- ROTA DE LOGOUT ---
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response

# --- ROTA DE SETUP ADMIN ---
@app.get("/setup-admin")
def setup_admin(db: Session = Depends(get_db)):
    try:
        meu_email = "redbull1782.mab@gmail.com" # Seu email conforme o sucesso anterior
        minha_senha = "sua_senha_aqui"

        user_exists = db.query(models.Usuario).filter(models.Usuario.email == meu_email).first()
        if not user_exists:
            novo_admin = models.Usuario(
                email=meu_email, 
                senha=pwd_context.hash(minha_senha), 
                coins=9999, 
                plano="master"
            )
            db.add(novo_admin)
            db.commit()
            return {"status": "Sucesso", "msg": f"Admin {meu_email} criado!"}
        return {"status": "Erro", "msg": "Admin já existe."}
    except Exception as e:
        return {"status": "Erro", "detalhes": str(e)}

# --- ROTAS VISUAIS PROTEGIDAS (O CORAÇÃO DA PROTEÇÃO) ---

def verificar_acesso(request: Request):
    """Função auxiliar para checar se o usuário tem o cookie de acesso"""
    token = request.cookies.get("access_token")
    if not token:
        return False
    return True

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Se já estiver logado e tentar entrar no login, manda pra home
    if verificar_acesso(request):
        return RedirectResponse(url="/")
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("base.html", {"request": request, "title": "Dashboard"})

@app.get("/gen-insights", response_class=HTMLResponse)
async def gen_insights_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("gen_insights.html", {"request": request, "title": "Gen Insights"})

@app.get("/paraphraser", response_class=HTMLResponse)
async def paraphraser_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("paraphraser.html", {"request": request, "title": "Text Transmuter"})

@app.get("/script-forge", response_class=HTMLResponse)
async def script_forge_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("script_forge.html", {"request": request, "title": "Script Forge"})

@app.get("/voice-synthesizer", response_class=HTMLResponse)
async def voice_synthesizer_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("voice_synthesizer.html", {"request": request, "title": "Voice Synthesizer"})

@app.get("/miner", response_class=HTMLResponse)
async def miner_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("miner.html", {"request": request, "title": "Miner"})

@app.get("/audio-mixer", response_class=HTMLResponse)
async def mixer_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("audio_mixer.html", {"request": request, "title": "Audio Mixer"})

@app.get("/meta-seo", response_class=HTMLResponse)
async def seo_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("meta_seo.html", {"request": request, "title": "Meta & SEO"})

@app.get("/thumb-maker", response_class=HTMLResponse)
async def thumb_page(request: Request):
    if not verificar_acesso(request): return RedirectResponse(url="/login")
    return templates.TemplateResponse("thumb_maker.html", {"request": request, "title": "Thumb Maker"})

# --- ROTA DE STATUS ---
@app.get("/api/status")
def check_status():
    return {"status": "online", "message": "Motores neurais rodando liso!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
