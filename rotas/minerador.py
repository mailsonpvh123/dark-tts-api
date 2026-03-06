import re
import requests
import html
import urllib.parse
import base64
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from sqlalchemy.orm import Session

import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Data Miner"])

class MinerGenericRequest(BaseModel):
    query: str
    traduzir: bool = True

# ==========================================
# UTILITÁRIOS DE DECODIFICAÇÃO E TRADUÇÃO
# ==========================================

def decodificar_google_url(url_google):
    """Extrai a URL real de um link encriptado do Google News via Base64."""
    if "articles/" not in url_google: return url_google
    try:
        # O link real está escondido no final da URL após o 'articles/'
        parte_encriptada = url_google.split("articles/")[1].split("?")[0]
        # Adiciona padding se necessário para o base64
        padding = len(parte_encriptada) % 4
        if padding: parte_encriptada += "=" * (4 - padding)
        
        decoded_bytes = base64.urlsafe_b64decode(parte_encriptada)
        # Limpeza de caracteres não-ASCII que o Google coloca no meio
        decoded_str = decoded_bytes.decode('latin-1')
        match = re.search(r'https?://[^\s"<>]+', decoded_str)
        return match.group(0) if match else url_google
    except:
        return url_google

def traduzir_seguro(texto, target='pt'):
    if not texto or len(texto.strip()) < 5: return texto
    try:
        # Traduzimos apenas os primeiros 3000 chars para evitar erro de TimeOut/Quota
        tradutor = GoogleTranslator(source='auto', target=target)
        return tradutor.translate(texto[:3000])
    except Exception as e:
        print(f"DEBUG TRADUTOR: {e}")
        return texto # Retorna original se falhar, evitando o Erro 500

def extrair_texto_profundo(url):
    """Mergulho via Jina AI com fallback cirúrgico."""
    url_real = decodificar_google_url(url)
    try:
        # X-Return-Format: markdown é essencial para o Gemini depois
        res = requests.get(f"https://r.jina.ai/{url_real}", timeout=12)
        if res.status_code == 200 and len(res.text) > 400:
            limpo = re.sub(r'\[.*?\]\(.*?\)', '', res.text) # Remove links markdown
            return limpo[:12000]
    except:
        pass
    return ""

# ==========================================
# ROTAS CORRIGIDAS
# ==========================================

@router.post("/miner/wiki")
async def miner_wiki(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if usuario.coins < 5: raise HTTPException(status_code=402, detail="Sem Coins")
    
    try:
        query_en = traduzir_seguro(req.query, 'en')
        # Buscamos na Wiki EN por ser mais completa
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query_en)}&format=json"
        r_search = requests.get(search_url, timeout=10).json()
        
        items = r_search.get('query', {}).get('search', [])
        if not items: return {"status": "sucesso", "data": [], "novo_saldo": usuario.coins}

        resultados = []
        for item in items[:4]:
            page_title = item['title']
            # Obtendo o texto puro (explaintext=1)
            content_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={urllib.parse.quote(page_title)}&format=json"
            r_content = requests.get(content_url, timeout=10).json()
            
            pages = r_content.get('query', {}).get('pages', {})
            for pid, pdata in pages.items():
                raw_text = pdata.get('extract', '')
                if len(raw_text) < 100: continue
                
                # Se traduzir falhar aqui, o 'traduzir_seguro' garante que não dê erro 500
                final_title = traduzir_seguro(page_title, 'pt') if req.traduzir else page_title
                final_text = traduzir_seguro(raw_text, 'pt') if req.traduzir else raw_text
                
                resultados.append({
                    "titulo": final_title,
                    "texto": final_text[:300] + "...",
                    "texto_completo": final_text,
                    "url": f"https://en.wikipedia.org/?curid={pid}",
                    "fonte": "Wikipedia"
                })

        usuario.coins -= 5
        db.commit()
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        # Se der erro aqui, agora sabemos exatamente o que é
        print(f"ERRO CRÍTICO WIKI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro na extração Wiki: {str(e)}")

@router.post("/miner/news")
async def miner_news(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if usuario.coins < 5: raise HTTPException(status_code=402, detail="Sem Coins")

    try:
        query_en = traduzir_seguro(req.query, 'en')
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query_en)}&hl=en-US&gl=US&ceid=US:en"
        res_rss = requests.get(rss_url, timeout=10)
        root = ET.fromstring(res_rss.text)
        
        resultados = []
        for item in root.findall('.//item')[:5]:
            link_encriptado = item.find('link').text
            titulo_original = item.find('title').text
            
            # MAGIA: Decodifica e entra no site real
            corpo_site = extrair_texto_profundo(link_encriptado)
            
            # Se o Jina falhou em ler o site, usa o resumo do RSS
            if not corpo_site:
                desc = item.find('description').text or ""
                corpo_site = re.sub(r'<[^>]+>', '', html.unescape(desc))

            resultados.append({
                "titulo": traduzir_seguro(titulo_original, 'pt') if req.traduzir else titulo_original,
                "texto": traduzir_seguro(corpo_site[:400], 'pt') if req.traduzir else corpo_site[:400],
                "texto_completo": traduzir_seguro(corpo_site, 'pt') if req.traduzir else corpo_site,
                "url": decodificar_google_url(link_encriptado),
                "fonte": "Google News"
            })

        usuario.coins -= 5
        db.commit()
        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        print(f"ERRO NEWS: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar notícias.")
