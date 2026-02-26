import uvicorn
import os
from datetime import datetime
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
from auth import criar_token_acesso, verificar_senha, get_usuario_atual

# Importa as rotas dos arquivos modulares
from rotas import minerador, voice_synth, audio_mixer, paraphraser, gen_insights, script_forge, meta_seo, thumb_maker, historico

# --- INICIALIZAÇÃO ---
app = FastAPI(
    title="Dark Creator OS - API",
    description="SaaS com Sistema de Coins e Tiers (Porto Velho/RO)",
    version="3.6"
)

# Cria as tabelas no banco de dados automaticamente
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

# --- ACOPLANDO AS ROTAS DE API ---
app.include_router(minerador.router)
app.include_router(voice_synth.router)
app.include_router(audio_mixer.router)
app.include_router(paraphraser.router)
app.include_router(gen_insights.router)
app.include_router(script_forge.router)
app.include_router(meta_seo.router)
app.include_router(thumb_maker.router)
app.include_router(historico.router) # Nova Rota do Histórico Acoplada!

# --- FUNÇÃO AUXILIAR DE SESSÃO ---
async def obter_user_ou_redirect(request: Request, db: Session):
    """Verifica se o usuário está logado e retorna o objeto dele ou None"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        user = await get_usuario_atual(request, db)
        return user
    except:
        return None

# --- ROTAS DE AUTENTICAÇÃO (API) ---

@app.post("/api/registrar")
async def registrar(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    email = data.get("email")
    senha = data.get("password")

    if db.query(models.Usuario).filter(models.Usuario.email == email).first():
        return JSONResponse(status_code=400, content={"status": "erro", "message": "E-mail já cadastrado."})

    # Criando usuário com o presente de 100 coins (1 vídeo grátis completo!)
    novo_usuario = models.Usuario(
        email=email,
        senha=pwd_context.hash(senha),
        tipo_plano="FREE",
        coins=100 
    )

    db.add(novo_usuario)
    db.commit()
    return JSONResponse(content={"status": "sucesso", "message": "Conta criada! 100 coins adicionadas."})

@app.post("/api/login")
async def login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    email = data.get("email")
    senha = data.get("password")

    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    
    if not usuario or not verificar_senha(senha, usuario.senha):
        return JSONResponse(status_code=401, content={"status": "erro", "message": "E-mail ou senha incorretos."})

    token = criar_token_acesso(data={"sub": usuario.email})
    
    response = JSONResponse(content={"status": "sucesso", "message": "Bem-vindo!"})
    # O cookie mantém o cara logado por 7 dias
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=60*60*24*7)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response

# --- ROTAS VISUAIS (TELA A TELA) ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if user: return RedirectResponse(url="/")
    return templates.TemplateResponse("login.html", {"request": request, "title": "Acesso Colorido"})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    # Agora renderiza a nova página de dashboard
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Dashboard", "user": user})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("base.html", {"request": request, "title": "Dashboard", "user": user})

@app.get("/gen-insights", response_class=HTMLResponse)
async def gen_insights_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("gen_insights.html", {"request": request, "title": "Gen Insights", "user": user})

@app.get("/paraphraser", response_class=HTMLResponse)
async def paraphraser_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("paraphraser.html", {"request": request, "title": "Text Transmuter", "user": user})

@app.get("/script-forge", response_class=HTMLResponse)
async def script_forge_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("script_forge.html", {"request": request, "title": "Script Forge", "user": user})

@app.get("/voice-synthesizer", response_class=HTMLResponse)
async def voice_synthesizer_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("voice_synthesizer.html", {"request": request, "title": "Voice Synthesizer", "user": user})

@app.get("/miner", response_class=HTMLResponse)
async def miner_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("miner.html", {"request": request, "title": "Miner", "user": user})

@app.get("/audio-mixer", response_class=HTMLResponse)
async def mixer_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("audio_mixer.html", {"request": request, "title": "Audio Mixer", "user": user})

@app.get("/meta-seo", response_class=HTMLResponse)
async def seo_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("meta_seo.html", {"request": request, "title": "Meta & SEO", "user": user})

@app.get("/thumb-maker", response_class=HTMLResponse)
async def thumb_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("thumb_maker.html", {"request": request, "title": "Thumb Maker", "user": user})

@app.get("/historico", response_class=HTMLResponse)
async def historico_page(request: Request, db: Session = Depends(get_db)):
    user = await obter_user_ou_redirect(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse("historico.html", {"request": request, "title": "Histórico de Produção", "user": user})

# --- SETUP INICIAL ADMIN ---
@app.get("/setup-admin")
def setup_admin(db: Session = Depends(get_db)):
    try:
        meu_email = "redbull782.mab@gmail.com"
        minha_senha = "SUA_SENHA_AQUI" 

        user = db.query(models.Usuario).filter(models.Usuario.email == meu_email).first()
        
        if not user:
            admin = models.Usuario(
                email=meu_email, 
                senha=pwd_context.hash(minha_senha), 
                coins=10000, 
                tipo_plano="PLUS"
            )
            db.add(admin)
            db.commit()
            return {"msg": "Admin master criado com sucesso!"}
        else:
            user.senha = pwd_context.hash(minha_senha)
            user.coins = 10000
            user.tipo_plano = "PLUS"
            db.commit()
            return {"msg": "Credenciais do Admin atualizadas com sucesso! Tente logar agora."}
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
