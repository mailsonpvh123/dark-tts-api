import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# 1. Captura e limpa a chave
chave_bruta = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

if not chave_bruta:
    print("ALERTA CRÍTICO: Chave do Gemini não encontrada no ambiente!")

# 2. Inicializa o cliente da nova SDK Oficial
# Se a chave estiver vazia, ele não quebra na inicialização, mas avisamos acima
client = genai.Client(api_key=chave_bruta) if chave_bruta else None

async def call_gemini(system_prompt, user_content):
    if not client:
        raise Exception("CHAVE API AUSENTE: Configure a GEMINI_API_KEY no Easypanel.")

    try:
        # 3. Na nova SDK, usamos client.aio para chamadas rápidas e assíncronas
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.75,
            )
        )
        
        return response.text

    except Exception as e:
        # Captura qualquer erro de rede, cota ou chave da nova SDK
        raise Exception(f"Erro na API Google GenAI: {str(e)}")

# (A função do Groq fica para o próximo passo)
