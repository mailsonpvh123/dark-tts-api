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
        raise HTTPException(status_code=500, detail="Chave da Groq (GROQ_API_KEY) não configurada no .env")

    try:
        audio_content = await file.read()
        
        # O PULO DO GATO: Barreira de Segurança de Tamanho
        tamanho_mb = len(audio_content) / (1024 * 1024)
        if tamanho_mb > 25:
            raise HTTPException(status_code=400, detail=f"Arquivo rejeitado ({tamanho_mb:.1f}MB). A API Neural aceita no máximo 25MB. Dica: Se exportou o áudio do Mixer em WAV, converta para MP3 antes de gerar legendas!")

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_KEY}"}
        
        data = {
            "model": "whisper-large-v3",
            "response_format": "srt", 
        }
        
        if language != "auto":
            data["language"] = language

        # Força o tipo para evitar que a API rejeite certas extensões
        content_type = file.content_type if file.content_type else "audio/mpeg"
        files = {"file": (file.filename, audio_content, content_type)}

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, data=data, files=files)
            
            if response.status_code != 200:
                # Captura o erro exato que a Groq está retornando
                try:
                    erro_api = response.json().get('error', {}).get('message', response.text)
                except:
                    erro_api = response.text
                raise Exception(f"Erro Groq: {erro_api}")
            
            srt_output = response.text
            
            # Converte o SRT num TXT simples removendo os tempos
            lines = srt_output.split('\n')
            txt_lines = []
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.isdigit(): continue  
                if '-->' in line: continue   
                txt_lines.append(line)
                
            txt_output = " ".join(txt_lines)
            
        return {"status": "sucesso", "srt": srt_output, "txt": txt_output}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
