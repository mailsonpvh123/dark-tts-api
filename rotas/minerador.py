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

def traduzir_seguro(texto, target='pt'):
    """Tradutor com redundância para evitar Erro 500"""
    if not texto or len(texto.strip()) < 3: return texto
    try:
        # Se for muito grande, pegamos apenas os primeiros 4500 caracteres para não travar a API gratuita
        texto_limpo = texto[:4500]
        return GoogleTranslator(source='auto', target=target).translate(texto_limpo)
    except Exception as e:
        print(f"Erro na tradução: {e}")
        return texto

# ==========================================
# MOTOR DE EXTRAÇÃO PROFUNDA (WEB SCRAPER V2)
# ==========================================
def extrair_texto_da_url(url):
    """
    Tenta invadir o site via Jina AI (Prioridade) para pegar o artigo completo. 
    Se falhar, retorna vazio para o sistema usar o resumo do RSS/Snippet.
    """
    if not url or not url.startswith('http'):
        return ""

    # Headers de elite para mimetizar um navegador real
    headers_browser = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    try:
        # TENTATIVA 1: Jina AI (O quebra-gelo de paywalls e SPAs)
        # Usamos um timeout agressivo para não travar o backend
        endpoint_jina = f"https://r.jina.ai/{url}"
        r_jina = requests.get(endpoint_jina, headers={'X-Return-Format': 'markdown'}, timeout=12)
        
        if r_jina.status_code == 200:
            content = r_jina.text
            # Limpeza rápida de ruído Markdown
            content = re.sub(r'!\[.*?\]\(.*?\)', '', content) # Remove imagens
            content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content) # Transforma links em texto
            
            # Validação de qualidade: se o Jina retornou aviso de bloqueio ou texto muito curto, descartamos
            if len(content) > 300 and "captcha" not in content.lower() and "blocked" not in content.lower():
                return content.strip()[:15000] # Limite de 15k chars para o Gemini não explodir
    except Exception as e:
        print(f"Falha Jina AI no link {url}: {e}")

    return "" 

# Custo Global do Minerador
CUSTO_MINER = 5

@router.post("/miner/reddit")
async def miner_reddit(req: MinerRedditRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail=f"Coins insuficientes!")
    
    try:
        query_en = traduzir_seguro(req.query, target='en')
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DarkCreator/2.0'}
        sub = req.sub.strip().replace('r/', '')
        
        url = f"https://www.reddit.com/r/{sub}/search.json?q={urllib.parse.quote(query_en)}&restrict_sr=1&type=link&limit=25&sort=relevance" if sub else f"https://www.reddit.com/search.json?q={urllib.parse.quote(query_en)}&type=link&limit=25&sort=relevance"
            
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        resultados = []
        
        for post in data.get('data', {}).get('children', []):
            p = post['data']
            texto_original = p.get('selftext', '')
            if len(texto_original.split()) < req.min_words or p.get('score', 0) < req.min_score: continue
            
            resultados.append({
                "titulo": p.get('title', ''),
                "texto": texto_original[:300] + "...", 
                "texto_completo": texto_original,      
                "url": f"https://reddit.com{p.get('permalink')}",
                "fonte": f"Reddit (r/{p.get('subreddit')})"
            })
            if len(resultados) >= 10: break
            
        usuario.coins -= CUSTO_MINER
        db.commit()
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/miner/news")
async def miner_news(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail="Coins insuficientes")

    try:
        query_en = traduzir_seguro(req.query, target='en')
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_en)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.text)
        resultados = []
        
        for item in root.findall('.//item')[:6]:
            titulo_original = item.find('title').text
            link_original = item.find('link').text
            
            # Extração Profunda via Jina
            corpo_completo = extrair_texto_da_url(link_original)
            
            # Fallback para o resumo do RSS se a extração falhar
            if not corpo_completo:
                desc_html = item.find('description').text or ""
                corpo_completo = re.sub(r'<[^>]+>', '', html.unescape(desc_html))

            if req.traduzir:
                titulo = traduzir_seguro(titulo_original, 'pt')
                texto_pt = traduzir_seguro(corpo_completo, 'pt')
            else:
                titulo = titulo_original
                texto_pt = corpo_completo

            resultados.append({
                "titulo": titulo,
                "texto": texto_pt[:250] + "...",
                "texto_completo": texto_pt,
                "url": link_original,
                "fonte": "Google News Global"
            })

        usuario.coins -= CUSTO_MINER
        db.commit()
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro News: {str(e)}")

@router.post("/miner/wiki")
async def miner_wiki(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail="Sem saldo")

    try:
        query_en = traduzir_seguro(req.query, target='en')
        # Busca na Wiki em Inglês (Sempre tem mais conteúdo)
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query_en)}&format=json"
        search_res = requests.get(search_url, timeout=10).json()
        
        resultados = []
        for item in search_res.get('query', {}).get('search', [])[:4]:
            page_title = item['title']
            
            # Pegando o conteúdo textual puro
            extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={urllib.parse.quote(page_title)}&format=json"
            ext_res = requests.get(extract_url, timeout=10).json()
            pages = ext_res.get('query', {}).get('pages', {})
            
            for pid, pdata in pages.items():
                content = pdata.get('extract', '')
                if len(content) < 100: continue
                
                if req.traduzir:
                    titulo_pt = traduzir_seguro(page_title, 'pt')
                    content_pt = traduzir_seguro(content, 'pt')
                else:
                    titulo_pt = page_title
                    content_pt = content

                resultados.append({
                    "titulo": titulo_pt,
                    "texto": content_pt[:300] + "...",
                    "texto_completo": content_pt,
                    "url": f"https://en.wikipedia.org/?curid={pid}",
                    "fonte": "Wikipedia Org."
                })

        usuario.coins -= CUSTO_MINER
        db.commit()
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro Wiki: {str(e)}")

@router.post("/miner/web")
async def miner_web(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    # Mantive a lógica do DuckDuckGo, mas agora o extrair_texto_da_url está muito mais forte!
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail="Coins insuficientes")
    try:
        query_en = traduzir_seguro(req.query, target='en')
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.post("https://html.duckduckgo.com/html/", data={'q': query_en}, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        resultados = []
        for a in soup.find_all('a', class_='result__snippet', limit=5):
            href = a.get('href', '')
            title_elem = a.find_previous('h2', class_='result__title')
            titulo_original = title_elem.text.strip() if title_elem else 'Site Encontrado'
            
            corpo_site = extrair_texto_da_url(href)
            if not corpo_site: corpo_site = a.text.strip()

            if req.traduzir:
                titulo = traduzir_seguro(titulo_original, 'pt')
                texto_pt = traduzir_seguro(corpo_site, 'pt')
            else:
                titulo = titulo_original
                texto_pt = corpo_site
                
            resultados.append({
                "titulo": titulo,
                "texto": texto_pt[:250] + "...",
                "texto_completo": texto_pt,
                "url": href,
                "fonte": "Deep Web Search"
            })

        usuario.coins -= CUSTO_MINER
        db.commit()
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
