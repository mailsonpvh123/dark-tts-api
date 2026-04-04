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

# AQUI ESTAVA O ERRO 404! Prefixo adicionado com sucesso.
router = APIRouter(prefix="/api/v1", tags=["Voice Synthesizer"])

# ==========================================
# ESTRUTURA DE DADOS (AGORA COM VELOCIDADE NO CINEMATIC)
# ==========================================
class AudioRequest(BaseModel):
    texto: str
    voz: str = "padrao-pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    temperatura: float = 0.7       
    estabilidade: float = 0.5      
    similaridade: float = 0.75     

# ==========================================
# CATÁLOGOS DE VOZES (100% WHITE-LABEL)
# ==========================================
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
    "Isonoe": ("Feminino", "Calma"),
    "Kore": ("Feminino", "Dinâmica"),
    "Kuma": ("Masculino", "Estável"),
    "Leda": ("Feminino", "Relaxada"),
    "Liriope": ("Feminino", "Acolhedora"),
    "Lysithea": ("Feminino", "Energética"),
    "Megaclite": ("Feminino", "Inquisitiva"),
    "Minkar": ("Masculino", "Autoridade (Documentários)"),
    "Nembus": ("Masculino", "Profunda e Grave"),
    "Puck": ("Masculino", "Expressiva e Contadora de Histórias"),
    "Puck (Recomendada)": ("Masculino", "Expressiva e Contadora de Histórias"),
    "Sinope": ("Feminino", "Ponderada"),
    "Sponde": ("Feminino", "Afiada"),
    "Surtur": ("Masculino", "Rasposa/Gravelly (Assustadora)"),
    "Tarqeq": ("Masculino", "Ressonante"),
    "Thebe": ("Feminino", "Quente e Acolhedora")
}

VOICES_CINEMATIC = {
    "eleven-marcus": ("Masculino", "Autoridade/Narrador Épico"),
    "eleven-adam": ("Masculino", "Profundo/Misterioso"),
    "eleven-antoni": ("Masculino", "Dinâmico/Jovem"),
    "eleven-arnold": ("Masculino", "Rouco/Suspense Sombrio"),
    "eleven-callum": ("Masculino", "Intenso/Cinematográfico"),
    "eleven-charlie": ("Masculino", "Casual/Conversacional"),
    "eleven-clyde": ("Masculino", "Grave/Documentário Guerra"),
    "eleven-daniel": ("Masculino", "Impactante/Jornalístico"),
    "eleven-domi": ("Feminino", "Forte/Agressiva"),
    "eleven-fin": ("Masculino", "Narrador de True Crime")
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

# ==========================================
# ROTAS DA API
# ==========================================
@router.get("/vozes")
async def listar_vozes():
    # 1. Padrão
    edge_voices = await edge_tts.list_voices()
    vozes_ptbr = []
    for v in edge_voices:
        if "pt-BR" in v["Locale"]:
            genero_br = "Feminino" if v["Gender"] == "Female" else "Masculino"
            vozes_ptbr.append({
                "Nome": v["ShortName"], 
                "Genero": f"{genero_br} | Voz Digital Neural", 
                "Tier": "padrao"
            })
    
    # 2. Creator
    vozes_creator = [
        {"Nome": k, "Genero": f"{v[0]} | {v[1]}", "Tier": "creator"} 
        for k, v in VOICES_CREATOR.items()
    ]
    
    # 3. Cinematic
    vozes_cinematic = [
        {"Nome": k, "Genero": f"{v[0]} | {v[1]}", "Tier": "cinematic"} 
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
            
            voice_id_map = {
                "eleven-marcus": "nPczCjzI2devNBz1zQrb", "eleven-adam": "pNInz6obpgDQGcFmaJgB",
                "eleven-antoni": "ErXwobaYiN019PkySvjV", "eleven-arnold": "VR6AewLTigWG4xSOukaG",
                "eleven-callum": "N2lVS1w4EtoT3dr4eOWO", "eleven-charlie": "IKne3meq5aSn9XLyUdCD",
                "eleven-clyde": "2EiwWnXFnvU5JabPnv8n", "eleven-daniel": "onwK4e9ZLuTAKqWW03F9",
                "eleven-domi": "AZnzlk1XvdvUeBnXmlld", "eleven-fin": "D38z5RcWu1voky8WS1ja"
            }
            voice_id = voice_id_map.get(req.voz, "pNInz6obpgDQGcFmaJgB")
            
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

            # Aplicação matemática de Velocidade (caso usuário mude no Cinematic)
            if req.velocidade != 1.0:
                try:
                    seg = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
                    # Ajuste de frame rate (Acelera sem perder qualidade no Pydub)
                    seg_mod = seg._spawn(seg.raw_data, overrides={"frame_rate": int(seg.frame_rate * req.velocidade)}).set_frame_rate(seg.frame_rate)
                    out = io.BytesIO()
                    seg_mod.export(out, format="mp3")
                    audio_data = out.getvalue()
                except Exception as err_speed:
                    print(f"Aviso: Não foi possível alterar a velocidade do áudio. {err_speed}")
            
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
        
        # SALVA NO DISCO
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
