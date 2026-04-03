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

# Chaves de API (Puxando do Easypanel)
GOOGLE_TTS_API_KEY = os.environ.get("GOOGLE_TTS_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

# Novo Elenco Google Cloud TTS
VOICES_CREATOR = [
    "pt-BR-Neural2-A", "pt-BR-Neural2-B", "pt-BR-Neural2-C", 
    "pt-BR-Wavenet-B", "pt-BR-Wavenet-A", "pt-BR-Wavenet-C"
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
    print("🚀 A iniciar o Gerador de Prévias (Limpeza Cirúrgica Ativada)...")
    
    # LIMPEZA CIRÚRGICA: Apaga apenas os fantasmas da OpenAI
    if os.path.exists(PASTA_DESTINO):
        print("🧹 A procurar ficheiros obsoletos do Tier Creator...")
        apagados = 0
        for nome_arquivo in os.listdir(PASTA_DESTINO):
            if nome_arquivo.startswith("creator-"):
                caminho_arquivo = os.path.join(PASTA_DESTINO, nome_arquivo)
                try:
                    os.remove(caminho_arquivo)
                    apagados += 1
                except Exception as e:
                    print(f"      ❌ Erro ao apagar {nome_arquivo}: {e}")
        print(f"✅ {apagados} ficheiros fantasmas do Creator eliminados! Prévias Cinematic e Standard preservadas.")
    else:
        os.makedirs(PASTA_DESTINO, exist_ok=True)

    # 1. GERANDO AS PRÉVIAS STANDARD (Edge TTS - Grátis)
    print("\n🎧 A gerar vozes Standard (Edge TTS)...")
    vozes_edge = await edge_tts.list_voices()
    for v in vozes_edge:
        if v["Locale"].startswith("pt-") or "Multilingual" in v["ShortName"]:
            short_name = f"padrao-{v['ShortName']}"
            caminho = os.path.join(PASTA_DESTINO, f"{short_name}.mp3")
            if not os.path.exists(caminho):
                print(f"   -> A gerar {short_name}...")
                communicate = edge_tts.Communicate(text=TEXTO_PREVIA, voice=v['ShortName'])
                await communicate.save(caminho)
            else:
                pass # Ficheiro já existe, salta silenciosamente para manter o terminal limpo

    # 2. GERANDO AS PRÉVIAS CREATOR (Google Cloud TTS)
    print("\n🎬 A gerar vozes Creator (Google Cloud TTS Neural2)...")
    if GOOGLE_TTS_API_KEY:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            for voz in VOICES_CREATOR:
                short_name = f"creator-{voz}"
                caminho = os.path.join(PASTA_DESTINO, f"{short_name}.mp3")
                
                if not os.path.exists(caminho):
                    print(f"   -> A gerar {short_name}...")
                    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "input": {"text": TEXTO_PREVIA},
                        "voice": {"languageCode": "pt-BR", "name": voz},
                        "audioConfig": {"audioEncoding": "MP3"}
                    }
                    
                    try:
                        resp = await http_client.post(url, json=data, headers=headers)
                        if resp.status_code == 200:
                            audio_b64 = resp.json().get("audioContent")
                            if audio_b64:
                                with open(caminho, "wb") as f:
                                    f.write(base64.b64decode(audio_b64))
                            else:
                                print(f"   ❌ Erro: Google não devolveu áudio para a voz {voz}.")
                        else:
                            print(f"   ❌ Erro Google TTS ({voz}): {resp.text}")
                    except Exception as e:
                        print(f"   ❌ Erro na Requisição Google TTS ({voz}): {e}")
                    
                    await asyncio.sleep(1)
                else:
                    print(f"   ✅ {short_name} já existe. A saltar...")
    else:
        print("   ⚠️ GOOGLE_TTS_API_KEY não encontrada. A saltar o nível Creator.")

    # 3. GERANDO AS PRÉVIAS CINEMATIC (ElevenLabs)
    print("\n⭐ A gerar vozes Cinematic (ElevenLabs)...")
    if ELEVENLABS_API_KEY:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            for voz_id, nome in VOICES_CINEMATIC.items():
                short_name = f"cinematic-{voz_id}"
                caminho = os.path.join(PASTA_DESTINO, f"{short_name}.mp3")
                
                if not os.path.exists(caminho):
                    print(f"   -> A gerar {nome} ({short_name})...")
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
                    print(f"   ✅ {short_name} já existe. Conta intacta, zero créditos gastos!")
    else:
        print("   ⚠️ ELEVENLABS_API_KEY não encontrada. A saltar o nível Cinematic.")

    print("\n✅ Todas as prévias foram sincronizadas com sucesso! Ficheiros fantasmas eliminados cirurgicamente.")

if __name__ == "__main__":
    asyncio.run(gerar_todas_as_previas())
