import edge_tts
import base64
import math
import os
import io
import time
import re
import textwrap
import httpx 
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pydub import AudioSegment

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(tags=["Voice Synthesizer"])

class AudioRequest(BaseModel):
    texto: str
    voz: str = "padrao-pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    temperatura: float = 0.7
    estabilidade: float = 0.5
    similaridade: float = 0.75

# ==========================================
# CATÁLOGOS DE VOZES PREMIUM
# ==========================================
VOICES_CREATOR = {
    "Achernar": {"desc": "Suave", "genero": "Feminino"},
    "Achird": {"desc": "Amigável", "genero": "Masculino"},
    "Algenib": {"desc": "Áspero", "genero": "Masculino"},
    "Algieba": {"desc": "Suave", "genero": "Masculino"},
    "Alnilam": {"desc": "Firme", "genero": "Masculino"},
    "Aoede": {"desc": "Breezy e Natural", "genero": "Feminino"},
    "Autonoe": {"desc": "Brilhante", "genero": "Feminino"},
    "Callirrhoe": {"desc": "Easy-going", "genero": "Feminino"},
    "Charon": {"desc": "Informativa (Dark/Suspense)", "genero": "Masculino"},
    "Despina": {"desc": "Smooth", "genero": "Feminino"},
    "Enceladus": {"desc": "Breathy", "genero": "Masculino"},
    "Erinome": {"desc": "Limpa", "genero": "Feminino"},
    "Fenrir": {"desc": "Excitável e Intenso", "genero": "Masculino"},
    "Gacrux": {"desc": "Adulto", "genero": "Feminino"},
    "Iapetus": {"desc": "Limpo", "genero": "Masculino"},
    "Kore": {"desc": "Firme", "genero": "Feminino"},
    "Laomedeia": {"desc": "Upbeat", "genero": "Feminino"},
    "Leda": {"desc": "Juventude", "genero": "Feminino"},
    "Orus": {"desc": "Firme", "genero": "Masculino"},
    "Pulcherrima": {"desc": "Avançar", "genero": "Feminino"},
    "Puck": {"desc": "Upbeat e Sarcástico", "genero": "Masculino"},
    "Rasalgethi": {"desc": "Informativa", "genero": "Masculino"},
    "Sadachbia": {"desc": "Lively", "genero": "Masculino"},
    "Sadaltager": {"desc": "Conhecimento", "genero": "Masculino"},
    "Schedar": {"desc": "Equilibrado", "genero": "Masculino"},
    "Sulafat": {"desc": "Quente", "genero": "Feminino"},
    "Umbriel": {"desc": "Tranquilo", "genero": "Masculino"},
    "Vindemiatrix": {"desc": "Gentle", "genero": "Feminino"},
    "Zephyr": {"desc": "Brilhante", "genero": "Feminino"},
    "Zubenelgenubi": {"desc": "Casual", "genero": "Masculino"}
}

VOICES_CINEMATIC = {
    "pNInz6obpgDQGcFmaJgB": {"nome": "Adam", "desc": "Dominante e Firme", "genero": "Masculino"},
    "Xb7hH8MSUJpSbSDYk0k2": {"nome": "Alice", "desc": "Clara, Educadora Envolvente", "genero": "Feminino"},
    "hpp4J3VqNfWAUOO0d1Us": {"nome": "Bella", "desc": "Profissional, Vibrante e Acolhedora", "genero": "Feminino"},
    "pqHfZKP75CvOlQylNhV4": {"nome": "Bill", "desc": "Sábio, Maduro e Equilibrado", "genero": "Masculino"},
    "nPczCjzI2devNBz1zQrb": {"nome": "Brian", "desc": "Profundo, Ressonante e Confortante", "genero": "Masculino"},
    "N2lVS1w4EtoT3dr4eOWO": {"nome": "Callum", "desc": "Rouco, Irreverente e Cativante", "genero": "Masculino"},
    "IKne3meq5aSn9XLyUdCD": {"nome": "Charlie", "desc": "Profundo, Confiante e Energético", "genero": "Masculino"},
    "iP95p4xoKVk53GoZ742B": {"nome": "Chris", "desc": "Charmoso e Pé no Chão", "genero": "Masculino"},
    "onwK4e9ZLuTAKqWW03F9": {"nome": "Daniel", "desc": "Locutor Estável e Seguro", "genero": "Masculino"},
    "cjVigY5qzO86Huf0OWal": {"nome": "Eric", "desc": "Suave e Confiável", "genero": "Masculino"},
    "JBFqnCBsd6RMkjVDRZzb": {"nome": "George", "desc": "Acolhedor, Narrador Cativante", "genero": "Masculino"},
    "SOYHLrjzK2X1ezoPC6cr": {"nome": "Harry", "desc": "Intenso e Feroz (Narrativa Épica)", "genero": "Masculino"},
    "cgSgspJ2msm6clMCkdW9": {"nome": "Jessica", "desc": "Divertida, Vibrante e Acolhedora", "genero": "Feminino"},
    "FGY2WhTYpPnrIDTdsKH5": {"nome": "Laura", "desc": "Entusiasta e Cheia de Atitude", "genero": "Feminino"},
    "TX3LPaxmHKxFdv7VOQHJ": {"nome": "Liam", "desc": "Energético (Criador de Conteúdo)", "genero": "Masculino"},
    "pFZP5JQG7iQjIQuC4Bku": {"nome": "Lily", "desc": "Voz Aveludada e Teatral", "genero": "Feminino"},
    "XrExE9yKIg1WjnnlVkGX": {"nome": "Matilda", "desc": "Profissional e Culta", "genero": "Feminino"},
    "SAz9YHcvj6GT2YYXdXww": {"nome": "River", "desc": "Relaxado, Neutro e Informativo", "genero": "Masculino"},
    "CwhRBWXzGAHq8TQ4Fs17": {"nome": "Roger", "desc": "Descontraído, Casual e Ressonante", "genero": "Masculino"},
    "EXAVITQu4vr4xnSDxMaL": {"nome": "Sarah", "desc": "Madura, Tranquilizadora e Confiante", "genero": "Feminino"},
    "bIHbv24MWmeRgasZH58o": {"nome": "Will", "desc": "Otimista e Relaxado", "genero": "Masculino"}
}

vozes_cache = []

@router.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    vozes_cache.clear() 
    
    try:
        for v_id, info in VOICES_CINEMATIC.items():
            vozes_cache.append({
                "name": info['nome'],
                "shortName": f"cinematic-{v_id}",
                "gender": info['genero'],
                "desc": info['desc'],
                "tipo": "cinematic"
            })

        for v_name, v_info in VOICES_CREATOR.items():
            vozes_cache.append({
                "name": v_name,
                "shortName": f"creator-{v_name}",
                "gender": v_info['genero'],
                "desc": v_info['desc'],
                "tipo": "creator"
            })
        
        voices = await edge_tts.list_voices()
        for v in voices:
            if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
                gen_pt = "Feminino" if v["Gender"] == "Female" else "Masculino"
                nome_limpo = v["ShortName"].replace('pt-BR-', '').replace('pt-PT-', '').replace('Neural', '').replace('Multilingual', '')
                vozes_cache.append({
                    "name": nome_limpo,
                    "shortName": f"padrao-{v['ShortName']}",
                    "gender": gen_pt,
                    "desc": "Voz Digital Neural",
                    "tipo": "padrao"
                })
        print(f"✅ {len(vozes_cache)} Vozes carregadas com sucesso na memória!")
    except Exception as e:
        print(f"❌ Erro ao carregar vozes: {e}")

@router.get("/vozes")
async def listar_vozes():
    if vozes_cache:
        return {"status": "sucesso", "vozes": vozes_cache}
    return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

def limpar_texto_para_voz(texto: str) -> str:
    t = texto.replace('*', '').replace('#', '').replace('_', '')
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\(.*?\)', '', t)
    return t.strip()

# ==========================================
# MOTOR MATEMÁTICO SRT
# ==========================================
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

def split_text_for_api(texto, max_chars=4000):
    texto = texto.replace('\n', ' ')
    frases = re.split(r'(?<=[.!?]) +', texto)
    chunks = []
    chunk_atual = ""
    for frase in frases:
        frase = frase.strip()
        if not frase: continue
        if len(chunk_atual) + len(frase) < max_chars:
            chunk_atual += frase + " "
        else:
            if chunk_atual: chunks.append(chunk_atual.strip())
            if len(frase) >= max_chars:
                pedacos = textwrap.wrap(frase, width=max_chars)
                for p in pedacos[:-1]: chunks.append(p.strip())
                chunk_atual = pedacos[-1] + " "
            else:
                chunk_atual = frase + " "
    if chunk_atual: chunks.append(chunk_atual.strip())
    return chunks

@router.post("/gerar_narracao")
async def gerar_narracao(
    req: AudioRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada.")
        
    texto = req.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="O texto para narração é obrigatório.")

    is_preview = texto.startswith("Olá, sou uma voz neural da sua plataforma.")
    
    is_cinematic = req.voz.startswith("cinematic-")
    is_creator = req.voz.startswith("creator-")
    
    tamanho_texto = len(texto)

    if is_preview:
        custo_operacao = 0
    elif is_cinematic:
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 50))
    elif is_creator:
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 10))
    else:
        custo_operacao = 30 

    if not is_preview:
        if usuario.coins < custo_operacao:
            raise HTTPException(status_code=402, detail=f"Coins insuficientes! Necessário {custo_operacao} coins.")
        usuario.coins -= custo_operacao
        db.commit()

    try:
        srt_content = ""
        audio_base64 = ""
        
        chunks = split_text_for_api(texto, max_chars=4000)
        final_audio = AudioSegment.empty()
        pause_seg = AudioSegment.silent(duration=300)

        if is_cinematic:
            api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
            modelo_eleven = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5").strip()
            
            if not api_key: raise ValueError("Chave ELEVENLABS_API_KEY não configurada. Configure no painel de ambiente.")
            
            voz_real = req.voz.replace("cinematic-", "")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                for i, chunk in enumerate(chunks):
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voz_real}"
                    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
                    data = {
                        "text": chunk,
                        "model_id": modelo_eleven,
                        "voice_settings": {
                            "stability": req.estabilidade,
                            "similarity_boost": req.similaridade
                        }
                    }
                    
                    response = await client.post(url, json=data, headers=headers)
                    if response.status_code != 200:
                        erro_msg = response.text if response.text else "Erro sem corpo na resposta."
                        raise Exception(f"Falha na API Cinematic (HTTP {response.status_code}): {erro_msg}")
                    
                    seg = AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
                    final_audio += (pause_seg + seg) if i > 0 else seg

            if req.velocidade != 1.0:
                final_audio = final_audio._spawn(final_audio.raw_data, overrides={"frame_rate": int(final_audio.frame_rate * req.velocidade)}).set_frame_rate(final_audio.frame_rate)

            mp3_io = io.BytesIO()
            final_audio.export(mp3_io, format="mp3", bitrate="128k")
            audio_final_bytes = mp3_io.getvalue()
            audio_base64 = base64.b64encode(audio_final_bytes).decode('utf-8')
            srt_content = gerar_srt_matematico(texto, audio_final_bytes)

        elif is_creator:
            api_key = os.environ.get("GEMINI_API_KEY_PAID", "").strip()
            modelo_gemini = os.environ.get("GEMINI_MODEL_VOICE", "gemini-2.5-flash-tts").strip()
            if not api_key: raise ValueError("Chave GEMINI_API_KEY_PAID não configurada no painel de ambiente.")

            voz_real = req.voz.replace("creator-", "")

            async with httpx.AsyncClient(timeout=120.0) as client:
                for i, chunk in enumerate(chunks):
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo_gemini}:generateContent?key={api_key}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "contents": [{"parts": [{"text": chunk}]}],
                        "generationConfig": {
                            "temperature": req.temperatura,
                            "responseModalities": ["AUDIO"],
                            "speechConfig": {
                                "voiceConfig": {
                                    "prebuiltVoiceConfig": {"voiceName": voz_real}
                                }
                            }
                        }
                    }
                    
                    max_retries = 3
                    audio_b64 = None
                    for attempt in range(max_retries):
                        try:
                            response = await client.post(url, json=data, headers=headers)
                            
                            if response.status_code != 200: 
                                erro_txt = response.text if response.text else "Nenhum texto retornado pela API."
                                raise Exception(f"HTTP {response.status_code} - {erro_txt}")
                            
                            resp_json = response.json()
                            
                            candidatos = resp_json.get('candidates', [])
                            if not candidatos:
                                raise Exception(f"API respondeu sem 'candidates'. Retorno: {response.text}")
                                
                            partes = candidatos[0].get('content', {}).get('parts', [])
                            for part in partes:
                                if 'inlineData' in part and part['inlineData'].get('mimeType', '').startswith('audio/'):
                                    audio_b64 = part['inlineData']['data']
                                    break
                                    
                            if audio_b64: 
                                break
                            else: 
                                raise Exception(f"A API do Gemini não retornou dados de áudio no JSON. Retorno: {response.text}")
                                
                        except Exception as api_err:
                            erro_detalhado = str(api_err) if str(api_err) else repr(api_err)
                            print(f"⚠️ Aviso (Tentativa {attempt+1}/{max_retries}): {erro_detalhado}")
                            
                            if attempt < max_retries - 1: 
                                time.sleep(3)
                            else: 
                                raise Exception(f"Detalhe Técnico do Google: {erro_detalhado}")
                    
                    audio_bytes = base64.b64decode(audio_b64)
                    seg = AudioSegment(data=audio_bytes, sample_width=2, frame_rate=24000, channels=1)
                    final_audio += (pause_seg + seg) if i > 0 else seg

            mp3_io = io.BytesIO()
            final_audio.export(mp3_io, format="mp3", bitrate="128k")
            audio_final_bytes = mp3_io.getvalue()
            audio_base64 = base64.b64encode(audio_final_bytes).decode('utf-8')
            srt_content = gerar_srt_matematico(texto, audio_final_bytes)

        else:
            voz_engine = req.voz.replace("padrao-", "") 
            velocidade_formatada = f"{int((req.velocidade - 1.0) * 100):+d}%"
            pitch_formatado = f"{req.pitch:+d}Hz"
            
            communicate = edge_tts.Communicate(text=texto, voice=voz_engine, rate=velocidade_formatada, pitch=pitch_formatado)
            submaker = edge_tts.SubMaker()
            audio_data = bytearray()
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
                elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    submaker.feed(chunk)
            
            srt_content = submaker.get_srt()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        if not is_preview:
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
                resultado=f"/static/audios/historico/{nome_arquivo}|SRT:{srt_content}",
                custo_coins=custo_operacao
            )
            db.add(novo_historico)
            db.commit()

        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content, "novo_saldo": usuario.coins}

    except Exception as e:
        if not is_preview:
            usuario.coins += custo_operacao
            db.commit()
        print(f"❌ Erro na Geração de Áudio: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na API Creator: {str(e)}")
