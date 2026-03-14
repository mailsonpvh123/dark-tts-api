import edge_tts
import base64
import math
import os
import io
import time
import re
import textwrap
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pydub import AudioSegment

from google import genai
from google.genai import types

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(tags=["Voice Synthesizer"])

class AudioRequest(BaseModel):
    texto: str
    voz: str = "pt-BR-AntonioNeural"
    velocidade: float = 1.0
    pitch: int = 0
    volume: int = 0
    temperatura: float = 1.0       
    instrucao_estilo: str = ""     

VOICES_MAP = {
    "Puck": "Animado / Jovem", "Charon": "Informativo / Grave", "Kore": "Firme / Madura",
    "Fenrir": "Excitado / Forte", "Leda": "Jovem / Articulada", "Orus": "Firme / Clássico",
    "Aoede": "Suave / Breezy", "Callirrhoe": "Relaxado", "Zephyr": "Brilhante / Enérgico",
    "Despina": "Suave", "Erinome": "Claro", "Algenib": "Áspero", 
    "Rasalgethi": "Informativo", "Laomedeia": "Animado", "Pulcherrima": "Avançado",
    "Achird": "Amigável", "Zubenelgenubi": "Casual", "Vindemiatrix": "Gentil",
    "Sadachbia": "Vivo", "Sadaltager": "Sábio", "Sulafat": "Caloroso"
}

vozes_cache = []

@router.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    vozes_cache.clear() 
    
    try:
        # Carrega Premium (Gemini)
        for v_name, v_desc in VOICES_MAP.items():
            vozes_cache.append({
                "name": f"{v_name} ({v_desc})",
                "shortName": f"gemini-premium-{v_name}",
                "gender": "Neutral",
                "tipo": "premium"
            })
        
        # Carrega Padrão (Edge TTS)
        voices = await edge_tts.list_voices()
        for v in voices:
            if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
                vozes_cache.append({
                    "name": v["Name"],
                    "shortName": v["ShortName"],
                    "gender": v["Gender"],
                    "tipo": "padrao"
                })
        print(f"✅ {len(vozes_cache)} Vozes carregadas com sucesso na memória!")
    except Exception as e:
        print(f"❌ Erro ao carregar vozes: {e}")

@router.get("/vozes")
async def listar_vozes():
    if vozes_cache:
        return {"status": "sucesso", "vozes": vozes_cache}
    else:
        return {"status": "erro", "mensagem": "Vozes ainda não carregadas no servidor."}

# ==========================================
# O CHUNKER NEURAL (Fatiador Avançado)
# ==========================================
def split_text_for_gemini(texto, max_chars=1200):
    """
    Cortado para 1200 caracteres (Micro-Chunking). 
    Garante que a IA nunca estoure o limite de saída de áudio e não gere "Apagões de Silêncio".
    """
    texto = re.sub(r'[*#""“”]', '', texto)
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
            if chunk_atual:
                chunks.append(chunk_atual.strip())
            
            if len(frase) >= max_chars:
                pedacos = textwrap.wrap(frase, width=max_chars)
                for p in pedacos[:-1]:
                    chunks.append(p.strip())
                chunk_atual = pedacos[-1] + " "
            else:
                chunk_atual = frase + " "
                
    if chunk_atual:
        chunks.append(chunk_atual.strip())
        
    return chunks

# ==========================================
# ROTA PRINCIPAL DE GERAÇÃO
# ==========================================
@router.post("/gerar_narracao")
async def gerar_narracao(
    req: AudioRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
        
    texto = req.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="O texto para narração é obrigatório.")

    is_premium = req.voz.startswith("gemini-premium")
    tamanho_texto = len(texto)

    # Cálculo dinâmico para vozes premium (sem limite)
    if is_premium:
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 10))
    else:
        custo_operacao = 30

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins.")

    usuario.coins -= custo_operacao
    db.commit()

    try:
        srt_content = ""
        audio_base64 = ""

        if is_premium:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key: raise ValueError("Chave GEMINI_API_KEY não configurada no Easypanel.")

            client = genai.Client(api_key=api_key)
            voz_real = req.voz.split("-")[-1] 

            # CABRESTO NEURAL: Mata as pausas dramáticas exageradas e alucinações
            instrucao_global = (
                "Você é um narrador profissional, focado e direto. "
                "REGRA DE OURO: Leia o texto fornecido IMEDIATAMENTE, sem introduções. "
                "Mantenha um ritmo de fala constante e fluido. NÃO faça pausas longas ou dramáticas entre as frases. "
                "Seja natural, em Português (Brasil)."
            )
            if req.instrucao_estilo:
                instrucao_global += f"\n\nDireção extra do diretor: {req.instrucao_estilo}"

            kwargs = {
                "response_modalities": ["AUDIO"],
                "temperature": req.temperatura,
                "system_instruction": instrucao_global,
                "speech_config": types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voz_real)
                    )
                )
            }

            chunks = split_text_for_gemini(texto, max_chars=1200)
            final_audio = AudioSegment.empty()
            
            # Reduzida a pausa de costura para 150ms (mais fluidez na fala contínua)
            pause_seg = AudioSegment.silent(duration=150)

            print(f"🎙️ Iniciando síntese Premium: {len(chunks)} partes micro-chunked. Custo: {custo_operacao} Coins.")

            for i, chunk in enumerate(chunks):
                pcm_data = None
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        try:
                            response = client.models.generate_content(
                                model="gemini-2.5-flash-preview-tts", 
                                contents=chunk, 
                                config=types.GenerateContentConfig(**kwargs)
                            )
                        except Exception as fallback_e:
                            if "404" in str(fallback_e) or "not found" in str(fallback_e).lower():
                                response = client.models.generate_content(
                                    model="gemini-2.5-flash-tts", 
                                    contents=chunk, 
                                    config=types.GenerateContentConfig(**kwargs)
                                )
                            else:
                                raise fallback_e
                        
                        pcm_data = next((part.inline_data.data for part in response.candidates[0].content.parts if part.inline_data), None)
                        if not pcm_data: raise ValueError("Resposta de áudio vazia.")
                        break
                        
                    except Exception as api_err:
                        err_str = str(api_err).lower()
                        print(f"⚠️ Aviso na Parte {i+1} (Tentativa {attempt+1}/{max_retries}): {api_err}")
                        
                        if "500" in err_str or "internal" in err_str:
                            if attempt == 0 and "system_instruction" in kwargs:
                                kwargs.pop("system_instruction")
                                print("♻️ Removendo Instrução de Estilo para contornar Erro 500...")
                                time.sleep(2)
                                continue
                            elif attempt < max_retries - 1:
                                time.sleep(5)
                                continue
                            else:
                                raise Exception("O servidor do Google falhou na geração. Tente novamente.")
                        elif "429" in err_str or "quota" in err_str:
                            if attempt < max_retries - 1:
                                time.sleep(10)
                                continue
                            else:
                                raise Exception("Cota da API do Google excedida.")
                        else:
                            raise api_err
                
                if not pcm_data:
                    raise Exception(f"Falha crítica ao gerar o bloco {i+1}.")

                seg = AudioSegment(data=pcm_data, sample_width=2, frame_rate=24000, channels=1)
                
                if i > 0:
                    final_audio += pause_seg + seg
                else:
                    final_audio += seg

            mp3_io = io.BytesIO()
            final_audio.export(mp3_io, format="mp3", bitrate="128k")
            audio_base64 = base64.b64encode(mp3_io.getvalue()).decode('utf-8')

        else:
            # --- ROTA PADRÃO (EDGE TTS) ---
            voz_engine = req.voz
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
        
        ferramenta_nome = "Voice Synth Premium" if is_premium else "Voice Synth Padrão"
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta=ferramenta_nome,
            input_usuario=f"Voz: {req.voz} | Tamanho: {tamanho_texto} chars",
            resultado="Áudio Costurado/Gerado com sucesso.", 
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "audio_base64": audio_base64, "srt": srt_content, "novo_saldo": usuario.coins}

    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro na Geração de Áudio: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao gerar o áudio: {str(e)}")
