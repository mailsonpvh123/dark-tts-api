from fastapi import APIRouter, HTTPException, File, UploadFile, Form
# Importe aqui as bibliotecas do Whisper (openai-whisper, tempfile, etc.)

router = APIRouter(tags=["Gen Legends"])

@router.post("/transcrever")
async def transcrever_audio(
    audio_file: UploadFile = File(...),
    idioma: str = Form("auto"),
    modelo: str = Form("base")
):
    try:
        # COLE AQUI SUA LÓGICA DO WHISPER AI
        
        return {"status": "sucesso", "txt": "...", "srt": "..."}
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}
