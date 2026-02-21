import edge_tts
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import uvicorn
import os
import re
import requests
import html
import urllib.parse
import xml.etree.ElementTree as ET
import shutil
import tempfile
from deep_translator import GoogleTranslator
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE DADOS ---
class AudioRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    volume: int = 0

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

# --- CACHE DE VOZES ---
vozes_cache = []

@app.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    try:
        voices = await edge_tts.list_voices()
        for v in voices:
            if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
                vozes_cache.append({
                    "name": v["Name"],
                    "shortName": v["ShortName"],
                    "gender": v["Gender"]
                })
        print(f"✅ {len(vozes_cache)} Vozes carregadas com sucesso na memória!")
    except Exception as e:
        print(f"❌ Erro ao carregar vozes: {e}")

@app.get("/vozes")
async def listar_vozes():
    if vozes_cache:
        return {"status": "sucesso", "vozes": vozes_cache}
    else:
        return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

# ==========================================
# 1. MOTOR DE VOZ
# ==========================================
@app.post("/gerar_narracao")
async def gerar_narracao(req: AudioRequest):
    try:
        velocidade_formatada = f"{int((req.velocidade - 1.0) * 100):+d}%"
        pitch_formatado = f"{req.pitch:+d}Hz"
        communicate = edge_tts.Communicate(text=req.texto, voice=req.voz, rate=velocidade_formatada, pitch=pitch_formatado)
        submaker = edge_tts.SubMaker()
        audio_data = bytearray()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
        
        srt_content = submaker.get_srt()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}

# ==========================================
# 2. EXTRATOR YOUTUBE
# ==========================================
@app.post("/extrair_youtube")
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

# ==========================================
# 3. MOTORES DE MINERAÇÃO (NUVEM)
# ==========================================
def traduzir_texto_longo(texto, source='auto', target='pt'):
    try:
        tradutor = GoogleTranslator(source=source, target=target)
        blocos = [texto[i:i+4000] for i in range(0, len(texto), 4000)]
        return " ".join([tradutor.translate(b) for b in blocos])
    except: return texto

@app.post("/miner/reddit")
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

@app.post("/miner/web")
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

@app.post("/miner/wiki")
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

@app.post("/miner/news")
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


# ==========================================
# 5. GERADOR DE LEGENDAS (WHISPER)
# ==========================================
def _fmt_ts(seconds: float) -> str:
    if seconds < 0: seconds = 0
    ms = int(round(seconds * 1000))
    hh = ms // 3600000
    ms -= hh * 3600000
    mm = ms // 60000
    ms -= mm * 60000
    ss = ms // 1000
    ms -= ss * 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

@app.post("/gen_legends")
async def gen_legends(
    file: UploadFile = File(...),
    model_size: str = Form("base"),
    language: str = Form("auto")
):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {"status": "erro", "mensagem": "Biblioteca faster-whisper não está instalada no servidor."}

    # Salva o arquivo de áudio temporariamente no servidor
    ext = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Carrega o modelo (Na primeira vez que rodar, o servidor vai baixar o modelo, pode levar uns segundos a mais)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        lang = None if language == "auto" else language
        
        # Faz a Mágica
        segments, info = model.transcribe(tmp_path, language=lang, beam_size=5, vad_filter=True)

        srt_lines = []
        txt_lines = []
        idx = 1
        
        for s in segments:
            start = _fmt_ts(s.start)
            end = _fmt_ts(s.end)
            text = re.sub(r"\s+", " ", s.text.strip())
            if not text: continue
            
            srt_lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
            txt_lines.append(text)
            idx += 1

        srt_content = "\n".join(srt_lines)
        txt_content = "\n\n".join(txt_lines)

        return {"status": "sucesso", "srt": srt_content, "txt": txt_content}
        
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro na transcrição: {str(e)}"}
    finally:
        # Limpa o lixo do servidor para não lotar o HD
        os.remove(tmp_path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
