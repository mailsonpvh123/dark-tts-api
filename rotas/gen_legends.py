import os
import re
import tempfile
import shutil
from fastapi import APIRouter, File, UploadFile, Form

router = APIRouter(tags=["Gen Legends"])

# Função Auxiliar
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

@router.post("/gen_legends")
async def gen_legends(
    file: UploadFile = File(...),
    model_size: str = Form("base"),
    language: str = Form("auto")
):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {"status": "erro", "mensagem": "Biblioteca faster-whisper não instalada."}

    ext = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        lang = None if language == "auto" else language
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
        return {"status": "erro", "mensagem": f"Erro: {str(e)}"}
    finally:
        os.remove(tmp_path)
