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
    sort: str = "top"        # relevance, top, new
    time_filter: str = "all" # all, year, month

class MinerGenericRequest(BaseModel):
    query: str
    traduzir: bool = True

def traduzir_seguro(texto, target='pt'):
    """Tradutor com redundância para evitar Erro 500"""
    if not texto or len(texto.strip()) < 3: return texto
    try:
        texto_limpo = texto[:4000]
        return GoogleTranslator(source='auto', target=target).translate(texto_limpo)
    except Exception as e:
        print(f"Erro na tradução: {e}")
        return texto

def extrair_texto_da_url(url):
    """Fallback via Jina AI exclusivo para Deep Web Search"""
    if not url or not url.startswith('http'):
        return ""
    try:
        endpoint_jina = f"https://r.jina.ai/{url}"
        r_jina = requests.get(endpoint_jina, headers={'X-Return-Format': 'markdown'}, timeout=12)
        if r_jina.status_code == 200:
            content = r_jina.text
            content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
            content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)
            if len(content) > 300 and "captcha" not in content.lower():
                return content.strip()[:15000]
    except:
        pass
    return "" 

CUSTO_MINER = 5

@router.post("/miner/reddit")
async def miner_reddit(req: MinerRedditRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail=f"Coins insuficientes!")
    
    try:
        # Dica Oculta: Se o usuário já escrever em inglês, não traduz.
        # Melhora a assertividade de "Golden Child" vs "Filhos Dourados".
        query_en = req.query if re.match(r'^[a-zA-Z0-9\s\-_]+$', req.query) else traduzir_seguro(req.query, target='en')
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DarkCreator/3.0'}
        sub = req.sub.strip().replace('r/', '')
        
        # URL MELHORADA: Agora usamos os parâmetros de SORT e TIME (Top All Time gera resultados 100x melhores)
        base_url = f"https://www.reddit.com/r/{sub}/search.json" if sub else "https://www.reddit.com/search.json"
        url = f"{base_url}?q={urllib.parse.quote(query_en)}&restrict_sr=1&type=link&limit=40&sort={req.sort}&t={req.time_filter}"
            
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            raise Exception("Reddit bloqueou a requisição. Tente novamente.")
            
        data = r.json()
        resultados = []
        
        for post in data.get('data', {}).get('children', []):
            p = post['data']
            texto_original = p.get('selftext', '')
            titulo_original = p.get('title', '')
            
            # FILTROS DE QUALIDADE (Mínimo de palavras e Score)
            if len(texto_original.split()) < req.min_words or p.get('score', 0) < req.min_score: 
                continue
                
            # A TRAVA DE ATUALIZAÇÃO AGORA FUNCIONA
            if req.sem_atualizacao and re.search(r'\b(update|updated|atualização)\b', titulo_original, re.IGNORECASE):
                continue
            
            resultados.append({
                "titulo": titulo_original,
                "texto": texto_original[:300] + "...", 
                "texto_completo": texto_original,      
                "url": f"https://reddit.com{p.get('permalink')}",
                "fonte": f"Reddit (r/{p.get('subreddit')})"
            })
            if len(resultados) >= 10: break
            
        usuario.coins -= CUSTO_MINER
        novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: Reddit | Query: {req.query}", resultado=f"{len(resultados)} posts.", custo_coins=CUSTO_MINER)
        db.add(novo_historico)
        db.commit()
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/miner/wiki")
async def miner_wiki(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail="Sem saldo")

    try:
        query_en = traduzir_seguro(req.query, target='en')
        headers = {'User-Agent': 'DarkCreatorBot/1.0 (https://darkcreator.app; admin@darkcreator.app) python-requests/2.31.0'}
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query_en)}&format=json"
        
        r_search = requests.get(search_url, headers=headers, timeout=10)
        
        try:
            search_res = r_search.json()
        except Exception as json_err:
            return {"status": "sucesso", "data": [], "novo_saldo": usuario.coins}
        
        resultados = []
        for item in search_res.get('query', {}).get('search', [])[:4]:
            page_title = item['title']
            extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={urllib.parse.quote(page_title)}&format=json"
            r_ext = requests.get(extract_url, headers=headers, timeout=10)
            
            try:
                ext_res = r_ext.json()
            except:
                continue
                
            pages = ext_res.get('query', {}).get('pages', {})
            
            for pid, pdata in pages.items():
                content = pdata.get('extract', '')
                if not content or len(content) < 100: continue
                
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

        if len(resultados) > 0:
            usuario.coins -= CUSTO_MINER
            novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: Wiki | Query: {req.query}", resultado=f"{len(resultados)} fatos.", custo_coins=CUSTO_MINER)
            db.add(novo_historico)
            db.commit()

        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro Wiki: Tente outro termo de busca.")

@router.post("/miner/news")
async def miner_news(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER: raise HTTPException(status_code=402, detail="Coins insuficientes")

    try:
        query_en = traduzir_seguro(req.query, target='en')
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_en)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.text)
        resultados = []
        
        for item in root.findall('.//item')[:5]:
            titulo_original = item.find('title').text
            link_original = item.find('link').text
            
            desc_html = item.find('description').text or ""
            corpo_completo = re.sub(r'<[^>]+>', '', html.unescape(desc_html))
            corpo_completo = re.sub(r'\s+', ' ', corpo_completo).strip()

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

        if len(resultados) > 0:
            usuario.coins -= CUSTO_MINER
            novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: News | Query: {req.query}", resultado=f"{len(resultados)} notícias.", custo_coins=CUSTO_MINER)
            db.add(novo_historico)
            db.commit()
            
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro News: {str(e)}")

@router.post("/miner/web")
async def miner_web(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario: raise HTTPException(status_code=401, detail="Sessão expirada.")
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

        if len(resultados) > 0:
            usuario.coins -= CUSTO_MINER
            novo_historico = models.Historico(usuario_id=usuario.id, ferramenta="Data Miner", input_usuario=f"Fonte: Web | Query: {req.query}", resultado=f"{len(resultados)} sites.", custo_coins=CUSTO_MINER)
            db.add(novo_historico)
            db.commit()
            
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
