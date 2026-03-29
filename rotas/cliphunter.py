from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import os
import requests
import random
from deep_translator import GoogleTranslator

router = APIRouter()

@router.get("/api/cliphunter/search")
async def search_media(
    query: str, 
    media_type: str = "video", # video, image, audio
    orientation: str = "landscape" # landscape, portrait, square
):
    if not query:
        raise HTTPException(status_code=400, detail="O termo de busca não pode estar vazio.")
        
    try:
        # Traduz para inglês para maximizar os resultados
        query_en = GoogleTranslator(source='auto', target='en').translate(query)
    except:
        query_en = query
        
    results = []
    
    pexels_key = os.getenv("PEXELS_API_KEY")
    pixabay_key = os.getenv("PIXABAY_API_KEY")
    
    # --- BUSCA DE VÍDEOS E IMAGENS ---
    if media_type in ["video", "image"]:
        
        # Orientação adaptada para a API do Pixabay
        pixabay_orient = "horizontal" if orientation == "landscape" else "vertical" if orientation == "portrait" else "all"
        
        # 1. BUSCA NO PEXELS
        if pexels_key:
            headers = {"Authorization": pexels_key}
            if media_type == "video":
                url = f"https://api.pexels.com/videos/search?query={query_en}&per_page=15&orientation={orientation}"
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    for v in r.json().get('videos', []):
                        link = next((f['link'] for f in v.get('video_files', []) if f['width'] >= 1280), v['video_files'][0]['link']) if v.get('video_files') else ""
                        results.append({
                            "id": f"pex_{v['id']}",
                            "type": "video",
                            "thumb": v['image'],
                            "url": link,
                            "duration": v['duration'],
                            "author": f"Pexels: {v['user']['name']}"
                        })
            else: # image
                url = f"https://api.pexels.com/v1/search?query={query_en}&per_page=15&orientation={orientation}"
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    for p in r.json().get('photos', []):
                        results.append({
                            "id": f"pex_{p['id']}",
                            "type": "image",
                            "thumb": p['src']['medium'],
                            "url": p['src']['original'],
                            "author": f"Pexels: {p['photographer']}"
                        })
                        
        # 2. BUSCA NO PIXABAY
        if pixabay_key:
            if media_type == "video":
                url = f"https://pixabay.com/api/videos/?key={pixabay_key}&q={query_en}&per_page=15"
                r = requests.get(url)
                if r.status_code == 200:
                    for v in r.json().get('hits', []):
                        video_urls = v.get('videos', {})
                        # Tenta pegar a melhor resolução disponível
                        best_video = video_urls.get('large', video_urls.get('medium', video_urls.get('tiny', {})))
                        link = best_video.get('url', '')
                        if link:
                            # Monta a thumbnail do vídeo do Pixabay
                            thumb = f"https://i.vimeocdn.com/video/{v['picture_id']}_640x360.jpg" if v.get('picture_id') else ""
                            results.append({
                                "id": f"pix_{v['id']}",
                                "type": "video",
                                "thumb": thumb,
                                "url": link,
                                "duration": v.get('duration', 0),
                                "author": f"Pixabay: {v.get('user', 'Anônimo')}"
                            })
            else: # image
                url = f"https://pixabay.com/api/?key={pixabay_key}&q={query_en}&orientation={pixabay_orient}&per_page=15"
                r = requests.get(url)
                if r.status_code == 200:
                    for p in r.json().get('hits', []):
                        results.append({
                            "id": f"pix_{p['id']}",
                            "type": "image",
                            "thumb": p.get('webformatURL'),
                            "url": p.get('largeImageURL'),
                            "author": f"Pixabay: {p.get('user', 'Anônimo')}"
                        })
        
        # Embaralha os resultados para misturar Pexels e Pixabay
        random.shuffle(results)
                
    # --- BUSCA NO FREESOUND (ÁUDIOS) ---
    elif media_type == "audio":
        freesound_key = os.getenv("FREESOUND_API_KEY")
        if not freesound_key:
            raise HTTPException(status_code=500, detail="Chave FREESOUND_API_KEY não configurada no servidor.")
            
        fields = "id,name,username,duration,previews"
        url = f"https://freesound.org/apiv2/search/text/?query={query_en}&token={freesound_key}&fields={fields}&page_size=15"
        r = requests.get(url)
        if r.status_code == 200:
            for a in r.json().get('results', []):
                preview = a.get('previews', {}).get('preview-hq-mp3')
                if preview:
                    results.append({
                        "id": f"fs_{a['id']}",
                        "type": "audio",
                        "title": a['name'][:50],
                        "url": preview,
                        "duration": round(a.get('duration', 0), 1),
                        "author": a['username']
                    })
                    
    return JSONResponse(content={"status": "sucesso", "query_original": query, "query_traduzida": query_en, "results": results})
