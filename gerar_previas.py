import asyncio
import os
import edge_tts
import httpx
from openai import AsyncOpenAI

# ==========================================
# CONFIGURAÇÕES
# ==========================================
TEXTO_PREVIA = "Olá, sou uma voz neural da sua plataforma. Esta é a minha qualidade de narração."
PASTA_DESTINO = os.path.join("frontend", "static", "audios", "previews")

# Chaves de API (Puxando do Easypanel)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

VOICES_CREATOR = ["alloy", "echo", "fable", "onyx", "nova", "shimmer", "ash", "coral", "sage"]

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
    print("🚀 Iniciando o Gerador de Prévias (Custo Zero para o Front-end)...")
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

    # 2. GERANDO AS PRÉVIAS CREATOR (OpenAI TTS)
    print("\n🎬 Gerando vozes Creator (OpenAI)...")
    if OPENAI_API_KEY:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        for voz in VOICES_CREATOR:
            short_name = f"creator-{voz}"
            caminho = os.path.join(PASTA_DESTINO, f"{short_name}.mp3")
            if not os.path.exists(caminho):
                print(f"   -> Gerando {short_name}...")
                try:
                    response = await client.audio.speech.create(model="tts-1", voice=voz, input=TEXTO_PREVIA)
                    with open(caminho, "wb") as f:
                        f.write(response.read())
                except Exception as e:
                    print(f"   ❌ Erro na OpenAI ({voz}): {e}")
    else:
        print("   ⚠️ OPENAI_API_KEY não encontrada. Pulando Creator.")

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
    else:
        print("   ⚠️ ELEVENLABS_API_KEY não encontrada. Pulando Cinematic.")

    print("\n✅ Todas as prévias foram geradas com sucesso! Seu front-end agora é instantâneo e custo zero.")

if __name__ == "__main__":
    asyncio.run(gerar_todas_as_previas())
