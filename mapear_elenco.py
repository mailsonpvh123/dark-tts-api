import asyncio
import os
import httpx

# Ele vai puxar a chave que você já configurou no Easypanel
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

async def rastrear_vozes():
    print("🔍 Conectando na ElevenLabs para mapear o seu elenco oficial...\n")
    
    if not ELEVENLABS_API_KEY:
        print("❌ ERRO: A chave ELEVENLABS_API_KEY não foi encontrada nas variáveis de ambiente.")
        return

    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Erro na API: {response.text}")
            return
            
        dados = response.json()
        
        print("=== COLE ESTE CÓDIGO NO SEU VOICE_SYNTH.PY ===\n")
        print("VOICES_CINEMATIC = {")
        
        for voz in dados.get("voices", []):
            # Filtra apenas as vozes "premade" (Padrão) que você viu no vídeo
            if voz.get("category") == "premade":
                voz_id = voz["voice_id"]
                nome = voz["name"]
                # Tenta pegar a descrição, se não tiver, coloca um texto genérico
                desc = voz.get("labels", {}).get("description", "Voz Nativa ElevenLabs")
                
                print(f'    "{voz_id}": {{"nome": "{nome}", "desc": "{desc}"}},')
                
        print("}")
        print("\n==============================================")
        
if __name__ == "__main__":
    asyncio.run(rastrear_vozes())
