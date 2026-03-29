from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import requests
from deep_translator import GoogleTranslator

# Substitua pela sua função real de banco de dados se precisar cobrar coins
# from database import get_db 

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
        # Traduz para inglês para maximizar os resultados nas APIs gringas
        query_en = GoogleTranslator(source='auto', target='en').translate(query)
    except:
        query_en = query
        
    results = []
    
    # --- BUSCA NO PEXELS (VÍDEOS E IMAGENS) ---
    if media_type in ["video", "image"]:
        pexels_key = os.getenv("PEXELS_API_KEY")
        if not pexels_key:
            raise HTTPException(status_code=500, detail="Chave PEXELS_API_KEY não configurada no servidor.")
            
        headers = {"Authorization": pexels_key}
        
        if media_type == "video":
            url = f"https://api.pexels.com/videos/search?query={query_en}&per_page=15&orientation={orientation}"
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                for v in data.get('videos', []):
                    # Pega a melhor resolução (pelo menos 720p/1080p)
                    link = next((file['link'] for file in v.get('video_files', []) if file['width'] >= 1280), v['video_files'][0]['link']) if v.get('video_files') else ""
                    results.append({
                        "id": v['id'],
                        "type": "video",
                        "thumb": v['image'],
                        "url": link,
                        "duration": v['duration'],
                        "author": v['user']['name']
                    })
        else: # image
            url = f"https://api.pexels.com/v1/search?query={query_en}&per_page=15&orientation={orientation}"
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                for p in data.get('photos', []):
                    results.append({
                        "id": p['id'],
                        "type": "image",
                        "thumb": p['src']['medium'],
                        "url": p['src']['original'],
                        "author": p['photographer']
                    })
                    
    # --- BUSCA NO FREESOUND (ÁUDIOS) ---
    elif media_type == "audio":
        freesound_key = os.getenv("FREESOUND_API_KEY")
        if not freesound_key:
            raise HTTPException(status_code=500, detail="Chave FREESOUND_API_KEY não configurada no servidor.")
            
        fields = "id,name,username,duration,previews"
        url = f"https://freesound.org/apiv2/search/text/?query={query_en}&token={freesound_key}&fields={fields}&page_size=15"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            for a in data.get('results', []):
                preview = a.get('previews', {}).get('preview-hq-mp3')
                if preview:
                    results.append({
                        "id": a['id'],
                        "type": "audio",
                        "title": a['name'][:50],
                        "url": preview,
                        "duration": round(a.get('duration', 0), 1),
                        "author": a['username']
                    })
                    
    return JSONResponse(content={"status": "sucesso", "query_original": query, "query_traduzida": query_en, "results": results})
