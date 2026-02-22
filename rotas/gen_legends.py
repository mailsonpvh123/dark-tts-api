import os
import base64
import tempfile
import shutil
from fastapi import APIRouter, File, UploadFile, Form

router = APIRouter(tags=["Audio Mixer Pro"])

# Função Auxiliar
def apply_limiter(seg, ceiling_dbfs):
    try:
        peak_dbfs = seg.max_dBFS
        if peak_dbfs == float("-inf") or peak_dbfs <= ceiling_dbfs:
            return seg
        reduce_db = ceiling_dbfs - peak_dbfs
        return seg.apply_gain(reduce_db)
    except: return seg

@router.post("/audio_mixer")
async def audio_mixer(
    voice_file: UploadFile = File(...),
    bg_file: UploadFile = File(...),
    voice_vol: float = Form(0.0),
    bg_vol: float = Form(-15.0),
    ducking: bool = Form(True),
    duck_amount: float = Form(-12.0),
    fade_in: int = Form(120),
    fade_out: int = Form(2000),
    trim_silence: bool = Form(True),
    trim_pad: int = Form(80),
    compressor: bool = Form(True),
    comp_th: float = Form(-18.0),
    comp_ratio: float = Form(4.0),
    comp_makeup: float = Form(3.0),
    limiter: bool = Form(True),
    limiter_ceil: float = Form(-1.0),
    eq_bass: float = Form(0.0),
    eq_treble: float = Form(0.0)
):
    try:
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        from pydub.effects import normalize, compress_dynamic_range
    except ImportError:
        return {"status": "erro", "mensagem": "Biblioteca pydub não está instalada."}

    v_ext = os.path.splitext(voice_file.filename)[1]
    b_ext = os.path.splitext(bg_file.filename)[1]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=v_ext) as v_tmp:
        shutil.copyfileobj(voice_file.file, v_tmp)
        v_path = v_tmp.name
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=b_ext) as b_tmp:
        shutil.copyfileobj(bg_file.file, b_tmp)
        b_path = b_tmp.name

    out_path = ""
    try:
        # Carrega os áudios (Pydub detecta MP3 ou WAV automaticamente)
        voice = AudioSegment.from_file(v_path)
        bg = AudioSegment.from_file(b_path)

        # 1. Corte de Silêncio
        if trim_silence and len(voice) > 0:
            ranges = detect_nonsilent(voice, min_silence_len=200, silence_thresh=-40.0, seek_step=10)
            if ranges:
                start = max(0, int(ranges[0][0] - trim_pad))
                end = min(len(voice), int(ranges[-1][1] + trim_pad))
                if end > start: voice = voice[start:end]

        # 2. Equalizador (Bass & Treble Boost)
        if eq_bass > 0:
            bass_seg = voice.low_pass_filter(250)
            voice = voice.overlay(bass_seg + eq_bass)
        if eq_treble > 0:
            treble_seg = voice.high_pass_filter(4000)
            voice = voice.overlay(treble_seg + eq_treble)

        # 3. Ganhos Manuais
        voice = voice + voice_vol
        bg = bg + bg_vol

        # 4. Cauda de Segurança
        tail_ms = fade_out if fade_out > 0 else 1500
        voice = voice + AudioSegment.silent(duration=tail_ms)

        # 5. Loop do Background
        if len(bg) > 0 and len(bg) < len(voice):
            loops = (len(voice) // len(bg)) + 1
            bg = bg * loops
        bg = bg[:len(voice)]

        # 6. Efeito Ducking Automático
        if ducking:
            window_ms = 150
            threshold_dbfs = -35.0
            out_bg = AudioSegment.empty()
            
            for i in range(0, len(voice), window_ms):
                v_chunk = voice[i:i + window_ms]
                b_chunk = bg[i:i + window_ms]
                if v_chunk.dBFS != float("-inf") and v_chunk.dBFS > threshold_dbfs:
                    b_chunk = b_chunk + duck_amount
                out_bg += b_chunk
            bg = out_bg

        # 7. Mixagem Final
        mixed = bg.overlay(voice)

        # 8. Efeitos Master: Fades, Compressor, Normalização e Limiter
        if fade_in > 0: mixed = mixed.fade_in(fade_in)
        if fade_out > 0: mixed = mixed.fade_out(fade_out)

        if compressor:
            mixed = compress_dynamic_range(mixed, threshold=comp_th, ratio=comp_ratio, attack=10, release=200)
            if comp_makeup > 0: mixed = mixed + comp_makeup

        mixed = normalize(mixed, headroom=1.0)

        if limiter:
            mixed = apply_limiter(mixed, limiter_ceil)

        # Exporta como MP3
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as out_tmp:
            out_path = out_tmp.name
            
        mixed.export(out_path, format="mp3", bitrate="192k")
        
        with open(out_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
            
        return {"status": "sucesso", "audio_base64": audio_base64}

    except Exception as e:
        return {"status": "erro", "mensagem": f"Falha na Mixagem: {str(e)}"}
    finally:
        os.remove(v_path)
        os.remove(b_path)
        if out_path and os.path.exists(out_path):
            os.remove(out_path)
