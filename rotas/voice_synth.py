import edge_tts
import base64
import math
import os
import io
import time
import re
import httpx 
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pydub import AudioSegment

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Voice Synthesizer"])

# ==========================================
# ESTRUTURA DE DADOS (COM TODOS OS CONTROLES)
# ==========================================
class AudioRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    temperatura: float = 0.7       
    estabilidade: float = 0.5      
    similaridade: float = 0.75     

# ==========================================
# CATÁLOGOS DE VOZES RESTAURADOS E BLINDADOS
# ==========================================
VOICES_STANDARD = {
    "pt-BR-AntonioNeural": "Masculino",
    "pt-BR-BrendaNeural": "Feminino",
    "pt-BR-DonatoNeural": "Masculino",
    "pt-BR-ElzaNeural": "Feminino",
    "pt-BR-FabioNeural": "Masculino",
    "pt-BR-GiovannaNeural": "Feminino",
    "pt-BR-HumbertoNeural": "Masculino",
    "pt-BR-JulioNeural": "Masculino",
    "pt-BR-LeilaNeural": "Feminino",
    "pt-BR-LeticiaNeural": "Feminino",
    "pt-BR-ManuelaNeural": "Feminino",
    "pt-BR-NicolauNeural": "Masculino",
    "pt-BR-ValerioNeural": "Masculino",
    "pt-BR-YaraNeural": "Feminino",
    "pt-PT-DuarteNeural": "Masculino",
    "pt-PT-FernandaNeural": "Feminino",
    "pt-PT-RaquelNeural": "Feminino",
    "en-US-AriaNeural": "Feminino (Inglês)",
    "en-US-ChristopherNeural": "Masculino (Inglês)",
    "en-US-EricNeural": "Masculino (Inglês)",
    "en-US-GuyNeural": "Masculino (Inglês)",
    "en-US-JennyNeural": "Feminino (Inglês)",
    "en-US-MichelleNeural": "Feminino (Inglês)"
}

VOICES_CREATOR = {
    "Achernar": ("Masculino", "Suave"),
    "Achird": ("Feminino", "Amigável"),
    "Algenib": ("Masculino", "Áspero"),
    "Algieba": ("Feminino", "Suave"),
    "Alnilam": ("Masculino", "Firme"),
    "Aoede": ("Feminino", "Breezy e Natural"),
    "Autonoe": ("Feminino", "Brilhante (Bright)"),
    "Callirrhoe": ("Feminino", "Easy-going"),
    "Charon": ("Masculino", "Informativa (Ideal p/ Dark e Suspense)"),
    "Despina": ("Feminino", "Smooth"),
    "Enceladus": ("Masculino", "Breathy"),
    "Erinome": ("Feminino", "Limpa"),
    "Fenrir": ("Masculino", "Excitável e Intenso"),
    "Gacrux": ("Masculino", "Adulto"),
    "Iapetus": ("Masculino", "Limpo"),
    "Kore": ("Feminino", "Firme"),
    "Laomedeia": ("Feminino", "Upbeat"),
    "Leda": ("Feminino", "Juventude"),
    "Orus": ("Masculino", "Firm"),
    "Pulcherrima": ("Feminino", "Avançar"),
    "Puck": ("Masculino", "Upbeat e Sarcástico"),
    "Rasalgethi": ("Masculino", "Informativa"),
    "Sadachbia": ("Feminino", "Lively"),
    "Sadaltager": ("Masculino", "Conhecimento"),
    "Schedar": ("Masculino", "Even"),
    "Sulafat": ("Feminino", "Quente"),
    "Umbriel": ("Masculino", "Tranquilo"),
    "Vindemiatrix": ("Feminino", "Gentle"),
    "Zephyr": ("Masculino", "Brilhante"),
    "Zubenelgenubi": ("Masculino", "Casual")
}

VOICES_CINEMATIC = {
    "Adam": ("Masculino", "Dominante e Firme", "pNInz6obpgDQGcFmaJgB"),
    "Alice": ("Feminino", "Clara, Educadora Envolvente", "Xb7hH8MSUJpSbSDYk0k2"),
    "Bella": ("Feminino", "Profissional, Vibrante e Acolhedora", "hpp4J3VqNfWAUOO0d1Us"),
    "Bill": ("Masculino", "Sábio, Maduro e Equilibrado", "pqHfZKP75CvOlQylNhV4"),
    "Brian": ("Masculino", "Profundo, Ressonante e Confortante", "nPczCjzI2devNBz1zQrb"),
    "Callum": ("Masculino", "Rouco, Irreverente e Cativante", "N2lVS1w4EtoT3dr4eOWO"),
    "Charlie": ("Masculino", "Profundo, Confiante e Energético", "IKne3meq5aSn9XLyUdCD"),
    "Chris": ("Masculino", "Charmoso e Pé no Chão", "iP95p4xoKVk53GoZ742B"),
    "Daniel": ("Masculino", "Locutor Estável e Seguro", "onwK4e9ZLuTAKqWW03F9"),
    "Eric": ("Masculino", "Suave e Confiável", "cjVigY5qzO86Huf0OWal"),
    "George": ("Masculino", "Acolhedor, Narrador Cativante", "JBFqnCBsd6RMkjVDRZzb"),
    "Harry": ("Masculino", "Intenso e Feroz (Narrativa Épica)", "SOYHLrjzK2X1ezoPC6cr"),
    "Jessica": ("Feminino", "Divertida, Vibrante e Acolhedora", "cgSgspJ2msm6clMCkdW9"),
    "Laura": ("Feminino", "Entusiasta e Cheia de Atitude", "FGY2WhTYpPnrIDTdsKH5"),
    "Liam": ("Masculino", "Energético (Criador de Conteúdo)", "TX3LPaxmHKxFdv7VOQHJ"),
    "Lily": ("Feminino", "Voz Aveludada e Teatral", "pFZP5JQG7iQjIQuC4Bku"),
    "Matilda": ("Feminino", "Profissional e Culta", "XrExE9yKIg1WjnnlVkGX"),
    "River": ("Masculino", "Relaxado, Neutro e Informativo", "SAz9YHcvj6GT2YYXdXww"),
    "Roger": ("Masculino", "Descontraído, Casual e Ressonante", "CwhRBWXzGAHq8TQ4Fs17"),
    "Sarah": ("Feminino", "Madura, Tranquilizadora e Confiante", "EXAVITQu4vr4xnSDxMaL"),
    "Will": ("Masculino", "Otimista e Relaxado", "bIHbv24MWmeRgasZH58o")
}

def limpar_texto_para_voz(texto: str) -> str:
    t = texto.replace('*', '').replace('#', '').replace('_', '')
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\(.*?\)', '', t)
    return t.strip()

def gerar_srt_matematico(texto, audio_bytes):
    try:
        audio_seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
        total_ms = len(audio_seg)
    except Exception as e:
        total_ms = len(texto) * 65 
    
    palavras = texto.split()
    if not palavras: return ""
    
    ms_por_palavra = total_ms / max(1, len(palavras))
    
    srt_output = []
    indice = 1
    tempo_atual_ms = 0
    tamanho_grupo = 6 
    
    for i in range(0, len(palavras), tamanho_grupo):
        grupo = palavras[i:i+tamanho_grupo]
        duracao_grupo = ms_por_palavra * len(grupo)
        
        inicio_ms = tempo_atual_ms
        fim_ms = tempo_atual_ms + duracao_grupo
        
        def ms_to_srt_time(ms):
            s, ms = divmod(int(ms), 1000)
            m, s = divmod(s, 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        
        srt_output.append(f"{indice}")
        srt_output.append(f"{ms_to_srt_time(inicio_ms)} --> {ms_to_srt_time(fim_ms)}")
        srt_output.append(" ".join(grupo))
        srt_output.append("")
        
        tempo_atual_ms = fim_ms
        indice += 1
        
    return "\n".join(srt_output)

@router.get("/vozes")
async def listar_vozes():
    # Retorna o ID original para buscar o preview e gerar a voz, mas um Nome limpo para o front
    vozes_ptbr = [
        {"Id": k, "Nome": k.replace('pt-BR-', '').replace('pt-PT-', '').replace('en-US-', '').replace('Neural', ''), "Genero": f"{v} | Padrão da Internet", "Tier": "padrao"} 
        for k, v in VOICES_STANDARD.items()
    ]
    
    vozes_creator = [
        {"Id": k, "Nome": k.replace(" (Recomendada)", ""), "Genero": f"{v[0]} | {v[1]}", "Tier": "creator"} 
        for k, v in VOICES_CREATOR.items()
    ]
    
    vozes_cinematic = [
        {"Id": k, "Nome": k, "Genero": f"{v[0]} | {v[1]}", "Tier": "cinematic"} 
        for k, v in VOICES_CINEMATIC.items()
    ]
    
    return vozes_ptbr + vozes_creator + vozes_cinematic

@router.post("/gerar_narracao")
async def gerar_narracao(
    req: AudioRequest, 
    db: Session = Depends(get_db), 
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada.")
    
    texto_limpo = limpar_texto_para_voz(req.texto)
    if not texto_limpo:
        raise HTTPException(status_code=400, detail="Texto inválido ou vazio.")

    is_creator = req.voz in VOICES_CREATOR
    is_cinematic = req.voz in VOICES_CINEMATIC

    tamanho_texto = len(texto_limpo)
    
    if is_cinematic:
        custo_operacao = max(100, math.ceil(tamanho_texto / 50.0))
    elif is_creator:
        custo_operacao = max(50, math.ceil(tamanho_texto / 100.0))
    else:
        custo_operacao = max(30, math.ceil(tamanho_texto / 200.0))

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Necessário {custo_operacao} coins.")

    usuario.coins -= custo_operacao
    db.commit()

    try:
        audio_data = b""
        srt_content = ""
        
        # 1. TIER CINEMATIC
        if is_cinematic:
            eleven_key = os.environ.get("ELEVENLABS_API_KEY")
            if not eleven_key: raise Exception("Motor Cinematic não configurado no servidor.")
            
            voice_id = VOICES_CINEMATIC[req.voz][2]
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": eleven_key}
            
            data = {
                "text": texto_limpo, 
                "model_id": "eleven_multilingual_v2", 
                "voice_settings": {
                    "stability": req.estabilidade, 
                    "similarity_boost": req.similaridade,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(url, json=data, headers=headers)
                if r.status_code != 200: raise Exception("Falha na geração do áudio. Tente novamente.")
                audio_data = r.content

            if req.velocidade != 1.0:
                try:
                    seg = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
                    seg_mod = seg._spawn(seg.raw_data, overrides={"frame_rate": int(seg.frame_rate * req.velocidade)}).set_frame_rate(seg.frame_rate)
                    out = io.BytesIO()
                    seg_mod.export(out, format="mp3")
                    audio_data = out.getvalue()
                except Exception as err_speed:
                    print(f"Aviso de velocidade: {err_speed}")
            
            srt_content = gerar_srt_matematico(texto_limpo, audio_data)
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        # 2. TIER CREATOR
        elif is_creator:
            api_key = os.environ.get("GEMINI_API_KEY_FREE") or os.environ.get("GEMINI_API_KEY")
            if not api_key: raise Exception("Motor Creator não configurado.")
            
            voz_id = req.voz.replace(" (Recomendada)", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-preview-tts:predict?key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "instances": [{"text": texto_limpo}],
                "parameters": {
                    "speech": {"voiceName": voz_id},
                    "temperature": req.temperatura
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(url, json=payload, headers=headers)
                if r.status_code != 200: raise Exception("Falha no servidor Neural Creator.")
                res_json = r.json()
                try:
                    audio_base64 = res_json['predictions'][0]['audioContent']
                    audio_data = base64.b64decode(audio_base64)
                except:
                    raise Exception("Falha ao extrair áudio da resposta.")
            
            srt_content = gerar_srt_matematico(texto_limpo, audio_data)

        # 3. TIER STANDARD
        else:
            communicate = edge_tts.Communicate(texto_limpo, req.voz, rate=f"{req.velocidade:+d}%", pitch=f"{req.pitch:+d}Hz")
            submaker = edge_tts.SubMaker()
            
            with io.BytesIO() as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        submaker.feed(chunk)
                audio_data = audio_file.getvalue()
            
            srt_content = submaker.get_srt()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        pasta_audios = os.path.join("frontend", "static", "audios", "historico")
        os.makedirs(pasta_audios, exist_ok=True)
        nome_arquivo = f"audio_{usuario.id}_{int(time.time())}.mp3"
        caminho_completo = os.path.join(pasta_audios, nome_arquivo)
        
        with open(caminho_completo, "wb") as f:
            f.write(base64.b64decode(audio_base64))
            
        ferramenta_nome = "Voice Synth - Cinematic" if is_cinematic else ("Voice Synth - Creator" if is_creator else "Voice Synth - Standard")
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta=ferramenta_nome,
            input_usuario=f"Voz: {req.voz} | Tamanho: {tamanho_texto} chars",
            resultado=f"/static/audios/historico/{nome_arquivo}",
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content, "novo_saldo": usuario.coins}

    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
