import os
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from faster_whisper import WhisperModel

router = APIRouter(prefix="/api/v1", tags=["Gen Legends"])

# Função para converter segundos em formato de tempo SRT (HH:MM:SS,mmm)
def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

@router.post("/gen_legends")
async def gerar_legendas(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model_size: str = Form("large")
):
    try:
        # 1. Salva o áudio recebido temporariamente no servidor
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # 2. Carrega o modelo local (Usando int8 no CPU para máxima velocidade e economia de RAM)
        modelo_real = "large-v3" if model_size == "large" else model_size
        model = WhisperModel(modelo_real, device="cpu", compute_type="int8")

        # 3. Transcreve o áudio
        lang_param = language if language != "auto" else None
        segments, info = model.transcribe(tmp_path, language=lang_param, beam_size=5)

        srt_lines = []
        txt_lines = []
        
        # 4. Monta os blocos de legenda SRT e o Texto Limpo
        for i, segment in enumerate(segments):
            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)
            text = segment.text.strip()
            
            # Formatação exata exigida pelo padrão .SRT
            srt_lines.append(f"{i+1}\n{start} --> {end}\n{text}\n")
            txt_lines.append(text)

        # 5. Apaga o arquivo temporário para não lotar o HD do servidor
        os.remove(tmp_path)

        srt_output = "\n".join(srt_lines)
        txt_output = " ".join(txt_lines)

        return {
            "status": "sucesso", 
            "srt": srt_output, 
            "txt": txt_output
        }

    except Exception as e:
        # Se algo der errado e o arquivo ainda existir, ele limpa.
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))
