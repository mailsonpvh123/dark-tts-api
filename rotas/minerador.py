import re
import requests
import html
import urllib.parse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from deep_translator import GoogleTranslator

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

@router.post("/miner/reddit")
async def miner_reddit(req: MinerRedditRequest):
    try:
        query_en = traduzir_para_en(req.query)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) DarkCreator/2.0'}
        
        sub = req.sub.strip().replace('r/', '')
        
        # CORREÇÃO: Aumentado o limit para 100 (máximo do Reddit) para garantir que ele ache histórias longas no meio do lixo
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
            
        return {"status": "sucesso", "data": resultados}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

@router.post("/miner/web")
async def miner_web(req: MinerGenericRequest):
    try:
        query_en = traduzir_para_en(req.query)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = "https://html.duckduckgo.com/html/"
        r = requests.post(url, data={'q': query_en}, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        resultados = []
        for a in soup.find_all('a', class_='result__snippet', limit=10):
            texto = a.text.strip()
            href = a.get('href', '')
            title_elem = a.find_previous('h2', class_='result__title')
            titulo = title_elem.text.strip() if title_elem else 'Sem Título'
            
            if req.traduzir:
                titulo = traduzir_para_pt(titulo)
                texto = traduzir_para_pt(texto)
                
            resultados.append({
                "titulo": titulo,
                "texto": texto,
                "texto_completo": texto,
                "url": href,
                "fonte": "Deep Web Search"
            })
        return {"status": "sucesso", "data": resultados}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

@router.post("/miner/news")
async def miner_news(req: MinerGenericRequest):
    try:
        query_en = traduzir_para_en(req.query)
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_en)}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=10)
        
        root = ET.fromstring(r.text)
        resultados = []
        
        for item in root.findall('.//item')[:10]:
            titulo = item.find('title').text if item.find('title') is not None else 'Sem título'
            link = item.find('link').text if item.find('link') is not None else ''
            desc_html = item.find('description').text if item.find('description') is not None else ''
            texto = re.sub(r'<[^>]+>', ' ', html.unescape(desc_html))
            texto = re.sub(r'\s+', ' ', texto).strip()
            
            if req.traduzir:
                titulo = traduzir_para_pt(titulo)
                texto = traduzir_para_pt(texto)
                
            resultados.append({
                "titulo": titulo,
                "texto": texto[:250] + "...",
                "texto_completo": texto,
                "url": link,
                "fonte": "Google News Global"
            })
        return {"status": "sucesso", "data": resultados}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

@router.post("/miner/wiki")
async def miner_wiki(req: MinerGenericRequest):
    try:
        query_en = traduzir_para_en(req.query)
        url_search = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query_en)}&utf8=&format=json"
        r_search = requests.get(url_search, timeout=10).json()
        
        resultados = []
        for item in r_search.get('query', {}).get('search', [])[:5]:
            title = item['title']
            
            url_extract = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&titles={urllib.parse.quote(title)}&format=json"
            r_ext = requests.get(url_extract, timeout=10).json()
            pages = r_ext.get('query', {}).get('pages', {})
            
            for page_id, page_data in pages.items():
                texto = page_data.get('extract', '')
                if not texto: continue
                
                titulo_pt = traduzir_para_pt(title) if req.traduzir else title
                texto_pt = traduzir_para_pt(texto) if req.traduzir else texto
                
                resultados.append({
                    "titulo": titulo_pt,
                    "texto": texto_pt[:250] + "...",
                    "texto_completo": texto_pt,
                    "url": f"https://en.wikipedia.org/?curid={page_id}",
                    "fonte": "Wikipedia Org."
                })
        return {"status": "sucesso", "data": resultados}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
