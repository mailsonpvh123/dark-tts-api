import asyncio
import os
import edge_tts
import httpx
import base64

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TEXTO_PREVIA = "Olá, sou uma voz neural da sua plataforma. Esta é a minha qualidade de narração."
PASTA_DESTINO = os.path.join("frontend", "static", "audios", "previews")

# Chaves e Modelos de API (Puxando do Easypanel conforme suas variáveis)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_PAID")
GEMINI_MODEL_VOICE = os.environ.get("GEMINI_MODEL_VOICE", "gemini-2.5-flash")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

# Novo Elenco Gemini Completo (30 Vozes)
VOICES_CREATOR = [
    "Achernar", "Achird", "Algenib", "Algieba", "Alnilam", "Aoede", 
    "Autonoe", "Callirrhoe", "Charon", "Despina", "Enceladus", 
    "Erinome", "Fenrir", "Gacrux", "Iapetus", "Kore", "Laomedeia", 
    "Leda", "Orus", "Pulcherrima", "Puck", "Rasalgethi", "Sadachbia", 
    "Sadaltager", "Schedar", "Sulafat", "Umbriel", "Vindemiatrix", 
    "Zephyr", "Zubenelgenubi"
]

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
    print("🚀 Iniciando o Gerador de Prévias (Com Sistema Anti-Rate Limit)...")
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
                                    with open(caminho, "wb") as f:
                                        f.write(base64.b64decode(audio_b64))
                                    break # Sai do loop de retry, sucesso!
                                else:
                                    print(f"   ❌ Erro: Gemini não retornou áudio para a voz {voz}.")
                                    break
                                    
                            elif resp.status_code == 429: # Rate Limit atingido
                                print(f"      ⚠️ API sobrecarregada (429). Freando por 12 segundos... (Tentativa {attempt+1}/{max_retries})")
                                await asyncio.sleep(12)
                            else:
                                print(f"   ❌ Erro Gemini ({voz}): {resp.text}")
                                break # Erro diferente de rate limit, desiste dessa voz e vai pra próxima
                                
                        except Exception as e:
                            print(f"   ❌ Erro na Requisição Gemini ({voz}): {e}")
                            await asyncio.sleep(5)
                    
                    # Pausa educada de 3 segundos entre as requisições para evitar tomar outro 429 atoa
                    await asyncio.sleep(3)
                else:
                    print(f"   ✅ {short_name} já existe. Pulando...")
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
                    
                    await asyncio.sleep(1) # Pausa leve na ElevenLabs
                else:
                    print(f"   ✅ {short_name} já existe. Pulando...")
    else:
        print("   ⚠️ ELEVENLABS_API_KEY não encontrada. Pulando Cinematic.")

    print("\n✅ Todas as prévias foram geradas com sucesso! Seu front-end agora é instantâneo e custo zero.")

if __name__ == "__main__":
    asyncio.run(gerar_todas_as_previas())
