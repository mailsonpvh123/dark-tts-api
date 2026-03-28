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

import openai

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
    instrucao_estilo: str = "" # Trazendo a Direção de Arte de volta para a IA Multimodal

# ==========================================
# CATÁLOGO OPENAI (VOZES PREMIUM)
# ==========================================
VOICES_MAP = {
    "alloy": "Andrógino / Versátil",
    "echo": "Masculino / Suave",
    "fable": "Masculino / Expressivo",
    "onyx": "Masculino / Grave e Sombrio (Ideal p/ Dark)",
    "nova": "Feminino / Clara e Energética",
    "shimmer": "Feminino / Acolhedora",
    "ash": "Masculino / Quente e Conversacional",
    "coral": "Feminino / Vibrante e Polida",
    "sage": "Andrógino / Calmo e Reflexivo"
}

vozes_cache = []

@router.on_event("startup")
async def carregar_vozes_memoria():
    global vozes_cache
    vozes_cache.clear() 
    
    try:
        # Carrega Premium (OpenAI)
        for v_name, v_desc in VOICES_MAP.items():
            vozes_cache.append({
                "name": f"{v_name.capitalize()} ({v_desc})",
                "shortName": f"openai-premium-{v_name}",
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
# O CHUNKER OTIMIZADO
# ==========================================
def split_text_for_openai(texto, max_chars=4000):
    texto = texto.replace('\n', ' ')
    frases = re.split(r'(?<=[.!?]) +', texto)
    
    chunks = []
    chunk_atual = ""
    
    for i, frase in enumerate(frases):
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

    # MODO FANTASMA
    is_preview = texto.startswith("Olá, sou uma voz neural da sua plataforma.")
    is_premium = req.voz.startswith("openai-premium")
    tamanho_texto = len(texto)

    # Cálculo de Custo Blindado (10 Coins por Minuto ~900 chars)
    if is_preview:
        custo_operacao = 0
    elif is_premium:
        custo_operacao = max(1, math.ceil((tamanho_texto / 900.0) * 10))
    else:
        custo_operacao = 30

    if not is_preview:
        if usuario.coins < custo_operacao:
            raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins.")
        usuario.coins -= custo_operacao
        db.commit()

    try:
        srt_content = ""
        audio_base64 = ""

        if is_premium:
            # === ROTA OPENAI MULTIMODAL (O Ator de Dublagem) ===
            api_key = os.environ.get("OPENAI_API_KEY")
            # Fallback agora é o GPT-4o-mini
            modelo_tts = os.environ.get("OPENAI_MODEL_TTS", "gpt-4o-mini") 
            
            if not api_key: raise ValueError("Chave OPENAI_API_KEY não configurada no Easypanel.")

            client = openai.AsyncOpenAI(api_key=api_key)
            voz_real = req.voz.split("-")[-1] 

            chunks = split_text_for_openai(texto, max_chars=4000)
            final_audio = AudioSegment.empty()
            
            pause_seg = AudioSegment.silent(duration=200) 

            # Montando a mente do Ator
            sys_prompt = "Você é um narrador profissional e dublador de elite para YouTube. Leia o texto fornecido pelo usuário com perfeição rítmica. Entregue APENAS o áudio lendo o texto, não adicione respostas em texto."
            if req.instrucao_estilo:
                sys_prompt += f" \n\nDIRETOR DE ARTE: {req.instrucao_estilo}"

            print(f"🎙️ Iniciando Dublagem Multimodal (Modelo: {modelo_tts} | Voz: {voz_real} | Partes: {len(chunks)}).")

            for i, chunk in enumerate(chunks):
                max_retries = 3
                audio_bytes = None
                
                for attempt in range(max_retries):
                    try:
                        # Chamada para o Chat Completions forçando saída de Áudio
                        response = await client.chat.completions.create(
                            model=modelo_tts,
                            modalities=["text", "audio"],
                            audio={"voice": voz_real, "format": "mp3"},
                            messages=[
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": chunk}
                            ]
                        )
                        
                        # Extrai a base64 gerada pela IA e converte em bytes
                        audio_b64_output = response.choices[0].message.audio.data
                        audio_bytes = base64.b64decode(audio_b64_output)
                        break 
                    except Exception as api_err:
                        print(f"⚠️ Aviso na Parte {i+1} (Tentativa {attempt+1}/{max_retries}): {api_err}")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                            continue
                        else:
                            raise Exception(f"A OpenAI falhou ao gerar a atuação da voz: {str(api_err)}")
                
                if not audio_bytes:
                    raise Exception(f"Falha crítica ao gerar o bloco {i+1}.")

                seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                
                if i > 0:
                    final_audio += pause_seg + seg
                else:
                    final_audio += seg

            mp3_io = io.BytesIO()
            final_audio.export(mp3_io, format="mp3", bitrate="128k")
            audio_base64 = base64.b64encode(mp3_io.getvalue()).decode('utf-8')

        else:
            # === ROTA PADRÃO (EDGE TTS) ===
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
        
        # SALVA NO DISCO SE NÃO FOR PREVIEW
        if not is_preview:
            pasta_audios = os.path.join("frontend", "static", "audios")
            os.makedirs(pasta_audios, exist_ok=True)
            nome_arquivo = f"audio_{usuario.id}_{int(time.time())}.mp3"
            caminho_completo = os.path.join(pasta_audios, nome_arquivo)
            
            with open(caminho_completo, "wb") as f:
                f.write(base64.b64decode(audio_base64))
                
            caminho_relativo = f"/static/audios/{nome_arquivo}"

            ferramenta_nome = "Voice Synth Premium" if is_premium else "Voice Synth Padrão"
            novo_historico = models.Historico(
                usuario_id=usuario.id,
                ferramenta=ferramenta_nome,
                input_usuario=f"Voz: {req.voz} | Tamanho: {tamanho_texto} chars\nDireção: {req.instrucao_estilo}",
                resultado=caminho_relativo,
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
        raise HTTPException(status_code=500, detail=f"Falha ao gerar o áudio: {str(e)}")
