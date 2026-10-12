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
    if not texto or len(texto.strip()) < 3:
        return texto
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
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER:
        raise HTTPException(status_code=402, detail="Coins insuficientes!")

    try:
        # Se o utilizador já escrever em inglês, não traduz
        query_en = req.query.strip() if re.match(r'^[a-zA-Z0-9\s\-_]+$', req.query.strip()) else traduzir_seguro(req.query.strip(), target='en')
        sub = req.sub.strip().replace('r/', '').replace('/', '')
        posts_brutos = []

        headers_padrao = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }

        # URL oficial do Reddit que será usada nos túneis proxy caso o IP da VPS seja bloqueado
        base_reddit = f"https://www.reddit.com/r/{sub}/search.json" if sub else "https://www.reddit.com/search.json"
        reddit_target_url = f"{base_reddit}?q={urllib.parse.quote(query_en)}&restrict_sr={'1' if sub else '0'}&type=link&limit=100&sort={req.sort}&t={req.time_filter}&raw_json=1"

        # =====================================================================
        # MOTOR 1: PullPush API (Espelho direto sem bloqueio de VPS)
        # =====================================================================
        try:
            pp_params = {
                "q": query_en,
                "size": 100,
                "sort": "desc",
                "sort_type": "score" if req.sort == "top" else "created_utc"
            }
            if sub:
                pp_params["subreddit"] = sub

            r_pp = requests.get(
                "https://api.pullpush.io/reddit/search/submission/",
                params=pp_params,
                headers=headers_padrao,
                timeout=12
            )
            if r_pp.status_code == 200:
                dados_pp = r_pp.json().get("data", [])
                if isinstance(dados_pp, list) and len(dados_pp) > 0:
                    posts_brutos.extend(dados_pp)
        except Exception as e1:
            print(f"[Miner v4.0] Aviso Motor 1 (PullPush): {e1}")

        # =====================================================================
        # MOTOR 2: Túnel Proxy CodeTabs -> Reddit Oficial JSON
        # =====================================================================
        if len(posts_brutos) < 10:
            try:
                proxy_codetabs = f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(reddit_target_url, safe='')}"
                r_ct = requests.get(proxy_codetabs, headers=headers_padrao, timeout=12)
                if r_ct.status_code == 200:
                    children = r_ct.json().get("data", {}).get("children", [])
                    posts_brutos.extend([c.get("data", {}) for c in children if isinstance(c, dict)])
            except Exception as e2:
                print(f"[Miner v4.0] Aviso Motor 2 (CodeTabs): {e2}")

        # =====================================================================
        # MOTOR 3: Túnel Proxy AllOrigins -> Reddit Oficial JSON
        # =====================================================================
        if len(posts_brutos) < 10:
            try:
                proxy_ao = f"https://api.allorigins.win/raw?url={urllib.parse.quote(reddit_target_url, safe='')}"
                r_ao = requests.get(proxy_ao, headers=headers_padrao, timeout=12)
                if r_ao.status_code == 200:
                    children = r_ao.json().get("data", {}).get("children", [])
                    posts_brutos.extend([c.get("data", {}) for c in children if isinstance(c, dict)])
            except Exception as e3:
                print(f"[Miner v4.0] Aviso Motor 3 (AllOrigins): {e3}")

        # =====================================================================
        # MOTOR 4: Arctic Shift API (Espelho secundário com busca em selftext)
        # =====================================================================
        if len(posts_brutos) < 10:
            try:
                subs_busca = [sub] if sub else ["nosleep", "TrueOffMyChest", "LetsNotMeet", "confession", "creepyencounters", "Paranormal"]
                for s_atual in subs_busca:
                    as_params = {
                        "subreddit": s_atual,
                        "selftext": query_en,
                        "limit": 40,
                        "sort": "desc"
                    }
                    r_as = requests.get(
                        "https://arctic-shift.photon-reddit.com/api/posts/search",
                        params=as_params,
                        headers=headers_padrao,
                        timeout=10
                    )
                    if r_as.status_code == 200:
                        dados_as = r_as.json().get("data", [])
                        if isinstance(dados_as, list):
                            posts_brutos.extend(dados_as)
                    if len(posts_brutos) >= 60:
                        break
            except Exception as e4:
                print(f"[Miner v4.0] Aviso Motor 4 (Arctic Shift): {e4}")

        # =====================================================================
        # MOTOR 5: Old Reddit JSON Direto
        # =====================================================================
        if not posts_brutos:
            try:
                old_url = reddit_target_url.replace("www.reddit.com", "old.reddit.com")
                r_old = requests.get(old_url, headers=headers_padrao, timeout=10)
                if r_old.status_code == 200:
                    children = r_old.json().get("data", {}).get("children", [])
                    posts_brutos.extend([c.get("data", {}) for c in children if isinstance(c, dict)])
            except Exception as e5:
                print(f"[Miner v4.0] Aviso Motor 5 (Old Reddit): {e5}")

        if not posts_brutos:
            raise Exception("[Miner v4.0] Nenhum resultado encontrado nos 5 motores de busca. Tente outro termo.")

        # Ordena sempre pelos mais votados se o filtro for 'top'
        if req.sort == "top":
            posts_brutos.sort(key=lambda x: int(x.get("score") or 0), reverse=True)

        resultados = []
        resultados_reserva = []
        urls_vistas = set()

        for p in posts_brutos:
            if not isinstance(p, dict):
                continue
            texto_original = (p.get("selftext") or "").strip()
            titulo_original = (p.get("title") or "").strip()
            score_post = int(p.get("score") or 0)

            # Ignora posts vazios ou apagados
            if not texto_original or texto_original in ("[deleted]", "[removed]"):
                continue

            # Trava de atualização (Ignorar posts de "Update")
            if req.sem_atualizacao and re.search(r'\b(update|updated|atualização)\b', titulo_original, re.IGNORECASE):
                continue

            # Verifica o mínimo de palavras
            if len(texto_original.split()) < req.min_words:
                continue

            sub_nome = p.get("subreddit", "reddit")
            permalink = p.get("permalink") or f"/r/{sub_nome}/comments/{p.get('id', '')}/"
            url_final = permalink if permalink.startswith("http") else f"https://reddit.com{permalink}"

            if url_final in urls_vistas:
                continue
            urls_vistas.add(url_final)

            item_formatado = {
                "titulo": titulo_original,
                "texto": texto_original[:300] + "...",
                "texto_completo": texto_original,
                "url": url_final,
                "fonte": f"Reddit (r/{sub_nome} | ⭐ {score_post})"
            }

            if score_post >= req.min_score:
                resultados.append(item_formatado)
            else:
                resultados_reserva.append(item_formatado)

            if len(resultados) >= 10:
                break

        # Se o filtro de Score Mínimo (ex: 500) foi rigoroso demais para o termo,
        # entrega as melhores histórias com o mínimo de palavras para não voltar vazio
        if not resultados and resultados_reserva:
            resultados = resultados_reserva[:10]

        if len(resultados) > 0:
            usuario.coins -= CUSTO_MINER
            novo_historico = models.Historico(
                usuario_id=usuario.id,
                ferramenta="Data Miner",
                input_usuario=f"Fonte: Reddit | Query: {req.query}",
                resultado=f"{len(resultados)} posts.",
                custo_coins=CUSTO_MINER
            )
            db.add(novo_historico)
            db.commit()

        return {"status": "sucesso", "data": resultados, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/miner/wiki")
async def miner_wiki(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER:
        raise HTTPException(status_code=402, detail="Sem saldo")

    try:
        query_en = traduzir_seguro(req.query, target='en')
        headers = {'User-Agent': 'DarkCreatorBot/1.0 (https://darkcreator.app; admin@darkcreator.app) python-requests/2.31.0'}
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query_en)}&format=json"
        
        r_search = requests.get(search_url, headers=headers, timeout=10)
        
        try:
            search_res = r_search.json()
        except Exception:
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
                if not content or len(content) < 100:
                    continue
                
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
    except Exception:
        raise HTTPException(status_code=500, detail="Erro Wiki: Tente outro termo de busca.")

@router.post("/miner/news")
async def miner_news(req: MinerGenericRequest, db: Session = Depends(get_db), usuario: models.Usuario = Depends(get_usuario_atual)):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER:
        raise HTTPException(status_code=402, detail="Coins insuficientes")

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
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada.")
    if usuario.coins < CUSTO_MINER:
        raise HTTPException(status_code=402, detail="Coins insuficientes")
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
            if not corpo_site:
                corpo_site = a.text.strip()

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
