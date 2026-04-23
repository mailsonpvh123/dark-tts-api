import uvicorn
import os
import uuid # <-- Importado para gerar as sessões únicas
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text # <-- Para atualizar o banco de dados
from passlib.context import CryptContext

# --- IMPORTS DO SISTEMA ---
import models
from database import engine, get_db
from auth import criar_token_acesso, verificar_senha, get_usuario_atual

# Importa as rotas dos arquivos modulares
from rotas import minerador, voice_synth, audio_mixer, paraphraser, gen_insights, script_forge, meta_seo, thumb_maker, historico, pagamentos, cliphunter, scenemaker

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

# --- ROTAS DE PÁGINAS HTML (FRONTEND) ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Dashboard", "user": usuario})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login"})

@app.get("/registro", response_class=HTMLResponse)
async def registro_page(request: Request):
    return templates.TemplateResponse("registro.html", {"request": request, "title": "Criar Conta"})

@app.get("/gen-insights", response_class=HTMLResponse)
async def page_insights(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("gen_insights.html", {"request": request, "title": "Gen Insights", "user": usuario})

@app.get("/miner", response_class=HTMLResponse)
async def page_miner(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("miner.html", {"request": request, "title": "Data Miner", "user": usuario})

@app.get("/paraphraser", response_class=HTMLResponse)
async def page_paraphraser(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("paraphraser.html", {"request": request, "title": "Text Transmuter", "user": usuario})

@app.get("/script-forge", response_class=HTMLResponse)
async def page_script(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("script_forge.html", {"request": request, "title": "Script Forge", "user": usuario})

@app.get("/voice-synthesizer", response_class=HTMLResponse)
async def page_voice(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("voice_synthesizer.html", {"request": request, "title": "Estúdio Neural", "user": usuario})

@app.get("/scenemaker", response_class=HTMLResponse)
async def page_scenemaker(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("scenemaker.html", {"request": request, "title": "SceneMaker", "user": usuario})

@app.get("/meta-seo", response_class=HTMLResponse)
async def page_seo(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("meta_seo.html", {"request": request, "title": "Meta & SEO", "user": usuario})

@app.get("/thumb-maker", response_class=HTMLResponse)
async def page_thumb(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("thumb_maker.html", {"request": request, "title": "Thumb Maker", "user": usuario})

@app.get("/clip-hunter", response_class=HTMLResponse)
async def page_cliphunter(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("clip_hunter.html", {"request": request, "title": "Clip Hunter", "user": usuario})

@app.get("/historico", response_class=HTMLResponse)
async def page_historico(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("historico.html", {"request": request, "title": "Histórico", "user": usuario})

@app.get("/planos", response_class=HTMLResponse)
async def page_planos(request: Request, db: Session = Depends(get_db)):
    usuario = await get_usuario_atual(request, db)
    if not usuario: return RedirectResponse(url="/login")
    return templates.TemplateResponse("planos.html", {"request": request, "title": "Comprar Coins", "user": usuario})

@app.get("/checkout")
async def render_checkout(request: Request, usuario: models.Usuario = Depends(get_usuario_atual)):
    return templates.TemplateResponse("checkout.html", {"request": request, "usuario": usuario})

@app.get("/obrigado")
async def render_obrigado(request: Request, usuario: models.Usuario = Depends(get_usuario_atual)):
    return templates.TemplateResponse("obrigado.html", {"request": request, "usuario": usuario})

@app.get("/saiba-mais", response_class=HTMLResponse)
async def page_saiba_mais(request: Request, db: Session = Depends(get_db)):
    # Usamos o get_usuario_atual para enviar o usuário caso ele esteja logado
    # Se ele for um visitante novo (deslogado), o 'usuario' será None e o template lida com isso.
    usuario = await get_usuario_atual(request, db)
    return templates.TemplateResponse("saiba_mais.html", {"request": request, "title": "Saiba Mais - Dark Creator OS", "user": usuario})


@app.post("/api/logout")
async def logout():
    response = JSONResponse(content={"msg": "Logout efetuado"})
    response.delete_cookie("access_token")
    return response

@app.post("/api/login")
async def login(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        email = data.get("email")
        senha = data.get("password")
        
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if not user or not verificar_senha(senha, user.senha):
            return JSONResponse(status_code=401, content={"message": "E-mail ou senha incorretos."})
        
        # --- PROTEÇÃO DE MÚLTIPLOS LOGINS (GERA SESSÃO ÚNICA) ---
        nova_sessao = str(uuid.uuid4())
        user.token_sessao = nova_sessao 
        db.commit()

        # Cria o token injetando a sessão
        token = criar_token_acesso({"sub": user.email, "session_id": nova_sessao})
        
        response = JSONResponse(content={"message": "Login realizado com sucesso"})
        response.set_cookie(key="access_token", value=token, httponly=True, max_age=7*24*60*60)
        return response
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.post("/api/registrar")
async def registrar(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        email = data.get("email")
        senha = data.get("password")
        
        existente = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if existente:
            return JSONResponse(status_code=400, content={"message": "Este e-mail já está em uso."})
        
        novo_user = models.Usuario(
            email=email,
            senha=pwd_context.hash(senha),
            coins=30
        )
        db.add(novo_user)
        db.commit()
        return JSONResponse(content={"message": "Conta criada com sucesso!"})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# --- INCLUSÃO DAS ROTAS MODULARES ---
app.include_router(historico.router)
app.include_router(minerador.router)
app.include_router(paraphraser.router)
app.include_router(gen_insights.router)
app.include_router(script_forge.router)
app.include_router(voice_synth.router)
app.include_router(audio_mixer.router)
app.include_router(meta_seo.router)
app.include_router(thumb_maker.router)
app.include_router(pagamentos.router)
app.include_router(cliphunter.router)
app.include_router(scenemaker.router)

# --- ATUALIZAÇÃO DO BANCO & CRIAÇÃO DE ADMIN ---
@app.get("/setup-admin")
def setup_admin(db: Session = Depends(get_db)):
    try:
        # 1. ATUALIZAÇÃO ESTRUTURAL DO BANCO DE DADOS
        try:
            # Tenta injetar a nova coluna caso o banco de dados seja antigo
            db.execute(text("ALTER TABLE usuarios ADD COLUMN token_sessao VARCHAR"))
            db.commit()
            print("Coluna 'token_sessao' adicionada com sucesso ao banco!")
        except Exception:
            # Se der erro, é porque a coluna já existe. Tudo tranquilo.
            pass 

        # 2. CRIAÇÃO OU ATUALIZAÇÃO DO ADMIN
        meu_email = "redbull782.mab@gmail.com"
        minha_senha = "18022006Lipe#" 

        user = db.query(models.Usuario).filter(models.Usuario.email == meu_email).first()
        
        if not user:
            admin = models.Usuario(
                email=meu_email, 
                senha=pwd_context.hash(minha_senha), 
                coins=12000, 
                tipo_plano="PRO"
            )
            db.add(admin)
            db.commit()
            return {"msg": "Admin master criado e estrutura de banco atualizada!"}
        else:
            user.senha = pwd_context.hash(minha_senha)
            user.coins = 10000
            user.tipo_plano = "PLUS"
            db.commit()
            return {"msg": "Estrutura do banco e credenciais do Admin atualizadas com sucesso! Faça login."}
            
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
