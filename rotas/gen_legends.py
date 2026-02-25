import os
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv

load_dotenv()
router = APIRouter(prefix="/api/v1", tags=["Gen Legends"])

GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

@router.post("/gen_legends")
async def gerar_legendas(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model_size: str = Form("large")
):
    if not GROQ_KEY:
        raise HTTPException(status_code=500, detail="Chave da Groq não configurada no servidor.")

    try:
        audio_content = await file.read()
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {GROQ_KEY}"
        }
        
        data = {
            "model": "whisper-large-v3",
            "response_format": "srt", 
        }
        
        if language != "auto":
            data["language"] = language

        files = {
            "file": (file.filename, audio_content, file.content_type or "audio/mpeg")
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, data=data, files=files)
            
            if response.status_code != 200:
                raise Exception(f"Erro da API Groq: {response.text}")
            
            srt_output = response.text
            
            # Converte o SRT num TXT simples removendo os tempos (00:00:00,000 --> ...)
            lines = srt_output.split('\n')
            txt_lines = []
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.isdigit(): continue  # Pula os números dos blocos
                if '-->' in line: continue   # Pula as linhas de tempo
                txt_lines.append(line)
                
            txt_output = " ".join(txt_lines)
            
        return {
            "status": "sucesso", 
            "srt": srt_output,
            "txt": txt_output
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
