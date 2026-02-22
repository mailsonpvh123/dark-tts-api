from fastapi import APIRouter
from pydantic import BaseModel
import re
import requests
import html
import urllib.parse
import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator
from youtube_transcript_api import YouTubeTranscriptApi

router = APIRouter(tags=["Minerador e Extrator"])

# Modelos
class YoutubeRequest(BaseModel):
    url: str

class MinerRedditRequest(BaseModel):
    sub: str
    query: str
    min_words: int
    min_score: int
    sem_atualizacao: bool

class MinerWebRequest(BaseModel):
    query: str
    traduzir: bool

class MinerWikiNewsRequest(BaseModel):
    query: str

# Função Auxiliar
def traduzir_texto_longo(texto, source='auto', target='pt'):
    try:
        tradutor = GoogleTranslator(source=source, target=target)
        blocos = [texto[i:i+4000] for i in range(0, len(texto), 4000)]
        return " ".join([tradutor.translate(b) for b in blocos])
    except: return texto

# Rotas
@router.post("/extrair_youtube")
async def extrair_youtube(req: YoutubeRequest):
    try:
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", req.url)
        if not match: return {"status": "erro", "mensagem": "Link inválido."}
        video_id = match.group(1)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try: transcript = transcript_list.find_transcript(['pt', 'pt-BR', 'en', 'es'])
        except: transcript = transcript_list.find_transcript([t.language_code for t in transcript_list])
        texto_completo = " ".join([t['text'] for t in transcript.fetch()])
        return {"status": "sucesso", "texto": texto_completo}
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro: {str(e)}"}

@router.post("/miner/reddit")
async def miner_reddit(req: MinerRedditRequest):
    try:
        termo_busca = req.query
        try: termo_busca = GoogleTranslator(source='auto', target='en').translate(req.query)
        except: pass
        if req.sem_atualizacao: termo_busca += " -update -title:update"
        sub = req.sub.strip().replace("r/", "").replace("/", "")
        endpoint = f"/r/{sub}/search.json?q={urllib.parse.quote(termo_busca)} self:yes&restrict_sr=1&sort=relevance&limit=100" if sub else f"/search.json?q={urllib.parse.quote(termo_busca)} self:yes&sort=relevance&limit=100"
        headers = {'User-Agent': 'DarkMinerBot/5.0 (Windows NT 10.0; Win64; x64)'}
        resultados = []
        after = None
        for _ in range(5):
            url_final = f"https://www.reddit.com{endpoint}"
            if after: url_final += f"&after={after}"
            r = requests.get(url_final, headers=headers)
            if r.status_code != 200: break
            data_json = r.json()
            posts = data_json.get('data', {}).get('children', [])
            after = data_json.get('data', {}).get('after')
            if not posts: break
            for post in posts:
                data = post['data']
                texto = data.get('selftext', '')
                word_count = len(texto.split())
                score = data.get('score', 0)
                if word_count < req.min_words or score < req.min_score: continue
                titulo = data.get('title', '')
                resultados.append({"titulo": titulo, "fonte": f"r/{data.get('subreddit')}", "url": f"https://reddit.com{data.get('permalink')}", "texto": texto, "palavras": word_count})
                if len(resultados) >= 10: break
            if len(resultados) >= 10 or not after: break
        if not resultados: return {"status": "erro", "mensagem": f"Nenhuma história encontrada! A sua régua está muito alta."}
        return {"status": "sucesso", "data": resultados}
    except Exception as e: return {"status": "erro", "mensagem": str(e)}

@router.post("/miner/web")
async def miner_web(req: MinerWebRequest):
    try:
        termo_busca = req.query
        if req.traduzir:
            try: termo_busca = GoogleTranslator(source='auto', target='en').translate(req.query)
            except: pass
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.post("https://lite.duckduckgo.com/lite/", data={"q": termo_busca}, headers=headers, timeout=10)
        links = list(set([l for l in re.findall(r'href="(http[s]?://[^"]+)"', r.text) if not any(x in l for x in ['duckduckgo', 'youtube', 'facebook'])]))[:5]
        resultados = []
        for link in links:
            try:
                page = requests.get(link, headers=headers, timeout=5)
                texto = re.sub(r'<[^>]+>', ' ', re.sub(r'<(style|script|header|footer|nav).*?</\1>', '', page.text, flags=re.DOTALL|re.IGNORECASE))
                texto = html.unescape(re.sub(r'\s+', ' ', texto).strip())
                if len(texto.split()) < 200: continue
                tit_match = re.search(r'<title>(.*?)</title>', page.text, re.IGNORECASE)
                titulo = html.unescape(tit_match.group(1)) if tit_match else "Artigo Web"
                if req.traduzir:
                    titulo = traduzir_texto_longo(titulo)
                    texto = traduzir_texto_longo(texto)
                resultados.append({"titulo": titulo, "fonte": "Web", "url": link, "texto": texto, "palavras": len(texto.split())})
            except: pass
        if not resultados: return {"status": "erro", "mensagem": "Nenhum artigo longo encontrado na Web."}
        return {"status": "sucesso", "data": resultados}
    except Exception as e: return {"status": "erro", "mensagem": str(e)}

@router.post("/miner/wiki")
async def miner_wiki(req: MinerWikiNewsRequest):
    headers = {'User-Agent': 'DarkCreatorBot/2.0'}
    try:
        r = requests.get("https://pt.wikipedia.org/w/api.php", params={"action": "opensearch", "search": req.query, "limit": "5", "format": "json"}, headers=headers)
        if r.status_code != 200: return {"status": "erro", "mensagem": f"Wikipedia bloqueou (HTTP {r.status_code})"}
        try: titulos = r.json()[1]
        except: return {"status": "erro", "mensagem": "Falha de Leitura."}
        resultados = []
        for tit in titulos:
            p = requests.get("https://pt.wikipedia.org/w/api.php", params={"action": "query", "prop": "extracts", "titles": tit, "explaintext": "1", "format": "json"}, headers=headers).json()
            for pid, pdata in p.get("query", {}).get("pages", {}).items():
                if pid != "-1" and pdata.get("extract"):
                    texto = pdata.get("extract")
                    resultados.append({"titulo": tit, "fonte": "Wikipedia PT", "url": "", "texto": texto, "palavras": len(texto.split())})
        if not resultados: return {"status": "erro", "mensagem": "Nenhum fato detalhado encontrado."}
        return {"status": "sucesso", "data": resultados}
    except Exception as e: return {"status": "erro", "mensagem": str(e)}

@router.post("/miner/news")
async def miner_news(req: MinerWikiNewsRequest):
    try:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(req.query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return {"status": "erro", "mensagem": f"Google News negou acesso"}
        try: root = ET.fromstring(r.text)
        except: return {"status": "erro", "mensagem": "Formato inválido."}
        resultados = []
        for item in root.findall('.//item')[:10]:
            titulo = item.find('title').text if item.find('title') is not None else 'Sem título'
            link = item.find('link').text if item.find('link') is not None else ''
            desc_html = item.find('description').text if item.find('description') is not None else ''
            texto = re.sub(r'<[^>]+>', ' ', html.unescape(desc_html))
            texto = re.sub(r'\s+', ' ', texto).strip()
            resultados.append({"titulo": titulo, "fonte": "Google News", "url": link, "texto": texto, "palavras": len(texto.split())})
        if not resultados: return {"status": "erro", "mensagem": "Nenhuma notícia encontrada."}
        return {"status": "sucesso", "data": resultados}
    except Exception as e: return {"status": "erro", "mensagem": str(e)}
