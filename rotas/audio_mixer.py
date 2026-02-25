import os
import base64
import tempfile
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydub import AudioSegment
from pydub.effects import compress_dynamic_range, normalize

router = APIRouter(prefix="/api/v1", tags=["Audio Mixer"])

def apply_limiter(seg, ceiling_dbfs):
    try:
        peak_dbfs = seg.max_dBFS
        if peak_dbfs == float("-inf") or peak_dbfs <= ceiling_dbfs:
            return seg
        reduce_db = ceiling_dbfs - peak_dbfs
        return seg.apply_gain(reduce_db)
    except:
        return seg

@router.post("/audio_mixer")
async def processar_mixer(
    voice_file: UploadFile = File(...),
    bg_file: UploadFile = File(...),
    voice_vol: float = Form(0.0),
    bg_vol: float = Form(-18.0),
    ducking: str = Form("true"),
    duck_amount: float = Form(-14.0),
    fade_in: int = Form(100),
    fade_out: int = Form(2500),
    trim_silence: str = Form("true"),
    trim_pad: int = Form(80),
    compressor: str = Form("true"),
    comp_th: float = Form(-18.0),
    comp_ratio: float = Form(4.0),
    comp_makeup: float = Form(4.0),
    limiter: str = Form("true"),
    limiter_ceil: float = Form(-1.0),
    eq_bass: float = Form(0.0),
    eq_treble: float = Form(0.0)
):
    try:
        # Salva os arquivos recebidos do Front-end temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_voice:
            temp_voice.write(await voice_file.read())
            temp_voice_path = temp_voice.name
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_bg:
            temp_bg.write(await bg_file.read())
            temp_bg_path = temp_bg.name

        # Carrega os áudios no motor PyDub
        voice = AudioSegment.from_file(temp_voice_path)
        bg = AudioSegment.from_file(temp_bg_path)
        
        # Limpa o lixo temporário do servidor
        os.remove(temp_voice_path)
        os.remove(temp_bg_path)

        # 1. Aplica o Ganho Base (Volume da UI)
        voice = voice + voice_vol
        bg = bg + bg_vol

        # 2. Equalizador (EQ Bass e Treble)
        if eq_bass > 0:
            low_freq = voice.low_pass_filter(250)
            voice = voice.overlay(low_freq + eq_bass)
        if eq_treble > 0:
            high_freq = voice.high_pass_filter(4000)
            voice = voice.overlay(high_freq + eq_treble)

        # 3. Ajuste de Tamanho (Loop ou Corte da música de fundo para caber na voz)
        if len(bg) < len(voice):
            bg = bg * (len(voice) // len(bg) + 1)
        bg = bg[:len(voice)]

        # 4. Auto-Ducking (Abaixa a música automaticamente quando o narrador fala)
        if ducking.lower() == 'true':
            window_ms = 100
            threshold_dbfs = -35
            out_bg = AudioSegment.empty()
            for i in range(0, len(voice), window_ms):
                v_chunk = voice[i:i + window_ms]
                b_chunk = bg[i:i + window_ms]
                if v_chunk.dBFS != float("-inf") and v_chunk.dBFS > threshold_dbfs:
                    b_chunk = b_chunk + duck_amount
                out_bg += b_chunk
            bg = out_bg

        # 5. Mistura as Tracks (Voz em cima do Background)
        mixed = bg.overlay(voice)

        # 6. Efeitos Master
        if fade_in > 0: mixed = mixed.fade_in(fade_in)
        if fade_out > 0: mixed = mixed.fade_out(fade_out)

        if compressor.lower() == 'true':
            mixed = compress_dynamic_range(mixed, threshold=comp_th, ratio=comp_ratio, attack=10, release=200)
            if comp_makeup > 0: mixed = mixed + comp_makeup

        mixed = normalize(mixed, headroom=1.0)

        if limiter.lower() == 'true':
            mixed = apply_limiter(mixed, limiter_ceil)

        # 7. Prepara o pacote WAV Final para o navegador
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_tmp:
            out_path = out_tmp.name
            
        mixed.export(out_path, format="wav")
        
        with open(out_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
            
        os.remove(out_path)
        
        return {"status": "sucesso", "audio_base64": audio_base64}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
