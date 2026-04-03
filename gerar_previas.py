import asyncio
import os
import edge_tts
import httpx
import base64
import shutil
import io
from pydub import AudioSegment

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TEXTO_PREVIA = "Olá, sou uma voz neural da sua plataforma. Esta é a minha qualidade de narração."
PASTA_DESTINO = os.path.join("frontend", "static", "audios", "previews")

# Chaves e Modelos de API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_PAID")
GEMINI_MODEL_VOICE = os.environ.get("GEMINI_MODEL_VOICE", "gemini-2.5-flash")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

# Elenco Gemini Oficial (5 Vozes base, sem gringos da OpenAI)
VOICES_CREATOR = ["Aoede", "Charon", "Fenrir", "Kore", "Puck"]

VOICES_CINEMATIC = {
    "pNInz6obpgDQGcFmaJgB": "Adam",
    "Xb7hH8MSUJpSbSDYk0k2": "Alice",
    "hpp4J3VqNfWAUOO0d1Us": "Bella",
    "pqHfZKP75CvOlQylNhV4": "Bill",
    "nPczCjzI2devNBz1zQrb": "Brian",
    "N2lVS1w4EtoT3dr4eOWO": "Callum",
    "IKne3meq5aSn9XLyUdCD": "Charlie",
    "iP95p4xoKVk53GoZ742B": "Chris",
    "onwK4e9ZLuTAKqWW03F9": "Daniel",
    "cjVigY5qzO86Huf0OWal": "Eric",
    "JBFqnCBsd6RMkjVDRZzb": "George",
    "SOYHLrjzK2X1ezoPC6cr": "Harry",
    "cgSgspJ2msm6clMCkdW9": "Jessica",
    "FGY2WhTYpPnrIDTdsKH5": "Laura",
    "TX3LPaxmHKxFdv7VOQHJ": "Liam",
    "pFZP5JQG7iQjIQuC4Bku": "Lily",
    "XrExE9yKIg1WjnnlVkGX": "Matilda",
    "SAz9YHcvj6GT2YYXdXww": "River",
    "CwhRBWXzGAHq8TQ4Fs17": "Roger",
    "EXAVITQu4vr4xnSDxMaL": "Sarah",
    "bIHbv24MWmeRgasZH58o": "Will"
}

async def gerar_todas_as_previas():
    print("🚀 Iniciando o Gerador de Prévias...")
    
    # MATA OS FANTASMAS DA OPENAI (Limpa a pasta antes de gerar)
    if os.path.exists(PASTA_DESTINO):
        shutil.rmtree(PASTA_DESTINO)
        print("🧹 Pasta de prévias limpa com sucesso. Fantasmas eliminados!")
    os.makedirs(PASTA_DESTINO, exist_ok=True)

    # 1. GERANDO AS PRÉVIAS STANDARD (Edge TTS - Grátis)
    print("\n🎧 Gerando vozes Standard (Edge TTS)...")
    vozes_edge = await edge_tts.list_voices()
    for v in vozes_edge:
        if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
            short_name = f"padrao-{v['ShortName']}"
            caminho = os.path.join(PASTA_DESTINO, f"{short_name}.mp3")
            if not os.path.exists(caminho):
                print(f"   -> Gerando {short_name}...")
                communicate = edge_tts.Communicate(text=TEXTO_PREVIA, voice=v['ShortName'])
                await communicate.save(caminho)

    # 2. GERANDO AS PRÉVIAS CREATOR (Gemini TTS)
    print(f"\n🎬 Gerando vozes Creator ({GEMINI_MODEL_VOICE})...")
    if GEMINI_API_KEY:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            for voz in VOICES_CREATOR:
                short_name = f"creator-{voz}"
                caminho = os.path.join(PASTA_DESTINO, f"{short_name}.mp3")
                
                if not os.path.exists(caminho):
                    print(f"   -> Gerando {short_name}...")
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_VOICE}:generateContent?key={GEMINI_API_KEY}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "contents": [{"parts": [{"text": TEXTO_PREVIA}]}],
                        "generationConfig": {
                            "responseModalities": ["AUDIO"],
                            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}
                        }
                    }
                    
                    max_retries = 4
                    for attempt in range(max_retries):
                        try:
                            resp = await http_client.post(url, json=data, headers=headers)
                            
                            if resp.status_code == 200:
                                resp_json = resp.json()
                                audio_b64 = None
                                for part in resp_json.get('candidates', [{}])[0].get('content', {}).get('parts', []):
                                    if 'inlineData' in part and part['inlineData']['mimeType'].startswith('audio/'):
                                        audio_b64 = part['inlineData']['data']
                                        break
                                
                                if audio_b64:
                                    # Corrige a codificação para MP3 usando o Pydub!
                                    audio_bytes = base64.b64decode(audio_b64)
                                    seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
                                    seg.export(caminho, format="mp3", bitrate="128k")
                                    break # Sucesso
                                else:
                                    print(f"   ❌ Erro: Gemini não retornou áudio para a voz {voz}.")
                                    break
                                    
                            elif resp.status_code == 429:
                                print(f"      ⚠️ API sobrecarregada (429). Freando por 12 segundos... (Tentativa {attempt+1}/{max_retries})")
                                await asyncio.sleep(12)
                            else:
                                print(f"   ❌ Erro Gemini ({voz}): {resp.text}")
                                break
                                
                        except Exception as e:
                            print(f"   ❌ Erro na Requisição Gemini ({voz}): {e}")
                            await asyncio.sleep(5)
                    
                    await asyncio.sleep(3) # Pausa educada
    else:
        print("   ⚠️ GEMINI_API_KEY_PAID não encontrada. Pulando Creator.")

    # 3. GERANDO AS PRÉVIAS CINEMATIC (ElevenLabs)
    print("\n⭐ Gerando vozes Cinematic (ElevenLabs)...")
    if ELEVENLABS_API_KEY:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            for voz_id, nome in VOICES_CINEMATIC.items():
                short_name = f"cinematic-{voz_id}"
                caminho = os.path.join(PASTA_DESTINO, f"{short_name}.mp3")
                
                if not os.path.exists(caminho):
                    print(f"   -> Gerando {nome} ({short_name})...")
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voz_id}"
                    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
                    data = {"text": TEXTO_PREVIA, "model_id": "eleven_turbo_v2_5"}
                    try:
                        resp = await http_client.post(url, json=data, headers=headers)
                        if resp.status_code == 200:
                            with open(caminho, "wb") as f:
                                f.write(resp.content)
                        else:
                            print(f"   ❌ Erro ElevenLabs ({nome}): {resp.text}")
                    except Exception as e:
                        print(f"   ❌ Erro na ElevenLabs ({nome}): {e}")
                    
                    await asyncio.sleep(1)
    else:
        print("   ⚠️ ELEVENLABS_API_KEY não encontrada. Pulando Cinematic.")

    print("\n✅ Todas as prévias foram geradas com sucesso! Seu front-end agora é instantâneo e custo zero.")

if __name__ == "__main__":
    asyncio.run(gerar_todas_as_previas())
