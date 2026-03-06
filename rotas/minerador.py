import re
import requests
import html
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Data Miner"])

class MinerRedditRequest(BaseModel):
    sub: str = ""
    query: str
    min_words: int = 100
    min_score: int = 10
    sem_atualizacao: bool = False

class MinerGenericRequest(BaseModel):
    query: str
    traduzir: bool = True

def traduzir_para_en(texto):
    if not texto: return ""
    try:
        return GoogleTranslator(source='auto', target='en').translate(texto)
    except:
        return texto

def traduzir_para_pt(texto):
    if not texto: return ""
    try:
        tradutor = GoogleTranslator(source='en', target='pt')
        blocos = [texto[i:i+4000] for i in range(0, len(texto), 4000)]
        return " ".join([tradutor.translate(b) for b in blocos])
    except:
        return texto

# ==========================================
# MOTOR DE EXTRAÇÃO PROFUNDA (WEB SCRAPER)
# ==========================================
def extrair_texto_da_url(url):
    """
    Motor definitivo: Usa o Jina AI (Arma Secreta) para furar Cloudflare e Paywalls.
    Se falhar, usa o Scraper Nativo com máscara do GoogleBot.
    """
    if not url or not url.startswith('http'):
        return ""
    
    # --- ARMA SECRETA: API DO JINA AI READER ---
    try:
        headers_jina = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        # O Jina AI resolve os redirecionamentos do Google e quebra paywalls de jornais
        r_jina = requests.get(f"https://r.jina.ai/{url}", headers=headers_jina, timeout=15)
        
        if r_jina.status_code == 200 and len(r_jina.text) > 100:
            texto_limpo = r_jina.text
            # Limpa o markdown (remove URLs de imagens e links) para não sujar o Paraphraser
            texto_limpo = re.sub(r'!\[.*?\]\(.*?\)', '', texto_limpo) 
            texto_limpo = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', texto_limpo)
            return texto_limpo.strip()[:15000]
    except Exception as e:
        print(f"Jina AI falhou, acionando Plano B... Erro: {e}")

    # --- PLANO B: SCRAPER NATIVO (BEAUTIFULSOUP) ---
    try:
        # Tenta resolver o link criptografado do Google News na marra
        if "news.google" in url or "consent.google" in url:
            try:
                r_redir = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup_redir = BeautifulSoup(r_redir.text, 'html.parser')
                a_tag = soup_redir.find('a', href=True)
                if a_tag and 'http' in a_tag['href'] and 'google.com' not in a_tag['href']:
                    url = a_tag['href']
            except:
                pass

        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Referer': 'https://www.google.com/'
        }
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        
        # Bloqueia código alienígena (Imagens, PDFs)
        content_type = r.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type:
            return ""

        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, 'html.parser')

        for elemento in soup(["script", "style", "nav", "header", "footer", "aside", "form", "button", "iframe", "noscript"]):
            elemento.extract()

        # Encontra a caixa de texto com mais parágrafos
        divs = soup.find_all(['article', 'main', 'div'])
        container = max(divs, key=lambda d: len(d.find_all('p'))) if divs else soup
        
        paragrafos = container.find_all(['p', 'h2', 'h3'])
        texto_nativo = "\n\n".join([p.get_text(separator=' ', strip=True) for p in paragrafos if len(p.get_text(strip=True)) > 25])

        if len(texto_nativo) < 300:
            texto_nativo = container.get_text(separator='\n', strip=True)
            linhas = [linha.strip() for linha in texto_nativo.split('\n') if len(linha.strip()) > 40]
            texto_nativo = "\n\n".join(linhas)

        return texto_nativo[:15000]
    except Exception as e:
        print(f"⚠️ Falha total ao extrair URL {url}. Detalhe: {e}")
        return ""

# Custo Global do Minerador
CUSTO_MINER = 5

@router.post("/miner/reddit")
async def miner_reddit(req: MinerRedditRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {CUSTO_MINER} coins para minerar.")
    
    try:
        query_en = traduzir_para_en(req.query)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DarkCreator/2.0'}
        sub = req.sub.strip().replace('r/', '')
        
        if sub:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={urllib.parse.quote(query_en)}&restrict_sr=1&type=link&limit=200&sort=relevance"
        else:
            url = f"https://www.reddit.com/search.json?q={urllib.parse.quote(query_en)}&type=link&limit=200&sort=relevance"
            
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            raise Exception("Reddit bloqueou a requisição. Tente novamente em alguns instantes.")
            
        data = r.json()
        resultados = []
        
        for post in data.get('data', {}).get('children', []):
            p = post['data']
            texto_original = p.get('selftext', '')
            
            if len(texto_original.split()) < req.min_words: continue
            if p.get('score', 0) < req.min_score: continue
            if req.sem_atualizacao and ("edit:" in texto_original.lower() or "update:" in texto_original.lower()): continue
            
            titulo_original = p.get('title', '')
            
            resultados.append({
                "titulo": titulo_original,
                "texto": texto_original[:250] + "...", 
                "texto_completo": texto_original,      
                "url": f"https://reddit.com{p.get('permalink')}",
                "fonte": f"Reddit (r/{p.get('subreddit')})"
            })
            
            if len(resultados) >= 10: break
            
        usuario.coins -= CUSTO_MINER
        novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: Reddit | Query: {req.query}", resultado=f"{len(resultados)} posts encontrados.", custo_coins=CUSTO_MINER)
        db.add(novo_historico)
        db.commit()
            
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/miner/web")
async def miner_web(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {CUSTO_MINER} coins para minerar.")

    try:
        query_en = traduzir_para_en(req.query)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = "https://html.duckduckgo.com/html/"
        r = requests.post(url, data={'q': query_en}, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        resultados = []
        for a in soup.find_all('a', class_='result__snippet', limit=5):
            texto_resumo = a.text.strip()
            href = a.get('href', '')
            title_elem = a.find_previous('h2', class_='result__title')
            titulo = title_elem.text.strip() if title_elem else 'Sem Título'
            
            texto_completo_site = extrair_texto_da_url(href)
            
            if len(texto_completo_site) < 100:
                texto_completo_site = texto_resumo

            if req.traduzir:
                titulo = traduzir_para_pt(titulo)
                texto_resumo = traduzir_para_pt(texto_resumo)
                texto_completo_site = traduzir_para_pt(texto_completo_site)
                
            resultados.append({
                "titulo": titulo,
                "texto": texto_resumo,
                "texto_completo": texto_completo_site,
                "url": href,
                "fonte": "Deep Web Search"
            })

        usuario.coins -= CUSTO_MINER
        novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: Web | Query: {req.query}", resultado=f"{len(resultados)} sites encontrados.", custo_coins=CUSTO_MINER)
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/miner/news")
async def miner_news(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {CUSTO_MINER} coins para minerar.")

    try:
        query_en = traduzir_para_en(req.query)
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_en)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=10)
        
        root = ET.fromstring(r.text)
        resultados = []
        
        for item in root.findall('.//item')[:5]:
            titulo = item.find('title').text if item.find('title') is not None else 'Sem título'
            link = item.find('link').text if item.find('link') is not None else ''
            
            # Limpando o resumo e evitando que ele seja apenas o título repetido
            desc_html = item.find('description').text if item.find('description') is not None else ''
            texto_resumo = re.sub(r'<[^>]+>', ' ', html.unescape(desc_html))
            texto_resumo = re.sub(r'\s+', ' ', texto_resumo).strip()
            if len(texto_resumo) <= len(titulo) + 20: 
                texto_resumo = "Resumo detalhado bloqueado pela fonte."
            
            texto_completo_site = extrair_texto_da_url(link)
            
            if len(texto_completo_site) < 100:
                texto_completo_site = texto_resumo
            
            if req.traduzir:
                titulo = traduzir_para_pt(titulo)
                if texto_resumo != "Resumo detalhado bloqueado pela fonte.":
                    texto_resumo = traduzir_para_pt(texto_resumo)
                texto_completo_site = traduzir_para_pt(texto_completo_site)
                
            resultados.append({
                "titulo": titulo,
                "texto": texto_resumo[:250] + "...",
                "texto_completo": texto_completo_site,
                "url": link,
                "fonte": "Google News Global"
            })

        usuario.coins -= CUSTO_MINER
        novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: News | Query: {req.query}", resultado=f"{len(resultados)} notícias encontradas.", custo_coins=CUSTO_MINER)
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/miner/wiki")
async def miner_wiki(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {CUSTO_MINER} coins para minerar.")

    try:
        query_en = traduzir_para_en(req.query)
        url_search = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query_en)}&utf8=&format=json"
        r_search = requests.get(url_search, timeout=10).json()
        
        resultados = []
        for item in r_search.get('query', {}).get('search', [])[:5]:
            title = item['title']
            
            url_extract = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={urllib.parse.quote(title)}&format=json"
            r_ext = requests.get(url_extract, timeout=10).json()
            pages = r_ext.get('query', {}).get('pages', {})
            
            for page_id, page_data in pages.items():
                texto_completo_wiki = page_data.get('extract', '')
                if not texto_completo_wiki: continue
                
                texto_resumo = texto_completo_wiki[:250] + "..."
                
                if req.traduzir:
                    titulo_pt = traduzir_para_pt(title)
                    texto_resumo = traduzir_para_pt(texto_resumo)
                    texto_completo_wiki = traduzir_para_pt(texto_completo_wiki)
                else:
                    titulo_pt = title
                
                resultados.append({
                    "titulo": titulo_pt,
                    "texto": texto_resumo,
                    "texto_completo": texto_completo_wiki,
                    "url": f"https://en.wikipedia.org/?curid={page_id}",
                    "fonte": "Wikipedia Org."
                })

        usuario.coins -= CUSTO_MINER
        novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: Wiki | Query: {req.query}", resultado=f"{len(resultados)} fatos encontrados.", custo_coins=CUSTO_MINER)
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
