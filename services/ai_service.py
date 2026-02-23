import os
import json
import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# ==========================================
# 1. TRATAMENTO DE CHAVES DE API
# ==========================================
# Captura e limpa as chaves para evitar erros por espaços em branco invisíveis
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")

if not GEMINI_KEY:
    print("ALERTA CRÍTICO: Chave do Gemini não encontrada no ambiente!")
if not GROQ_KEY:
    print("ALERTA CRÍTICO: Chave do Groq não encontrada no ambiente!")

# Inicializa o cliente da nova SDK Oficial do Google (se a chave existir)
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None


# ==========================================
# 2. MOTOR GEMINI (Paraphraser, SEO, Script)
# ==========================================
async def call_gemini(system_prompt, user_content):
    if not client:
        raise Exception("CHAVE API AUSENTE: Configure a GEMINI_API_KEY no Easypanel.")

    try:
        # Chamada assíncrona oficial da nova biblioteca google-genai
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
        raise Exception(f"Erro na API Google GenAI: {str(e)}")


# ==========================================
# 3. MOTOR GROQ (Gen Insights - Retorno JSON)
# ==========================================
async def call_groq_json(system_prompt, user_content):
    if not GROQ_KEY:
        raise Exception("CHAVE API AUSENTE: Configure a GROQ_API_KEY no Easypanel.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        # Força o Llama 3 a devolver exclusivamente um JSON válido
        "response_format": {"type": "json_object"},
        "temperature": 0.7
    }

    try:
        # Usa httpx para fazer a requisição direta à API do Groq
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            response = await http_client.post(url, headers=headers, json=payload)
            
            # Tratamento de erro específico se o Groq barrar a requisição
            if response.status_code != 200:
                data = response.json()
                erro_msg = data.get("error", {}).get("message", "Motivo desconhecido")
                raise Exception(f"O Groq Recusou [Status {response.status_code}]: {erro_msg}")
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
    except httpx.RequestError as e:
        raise Exception(f"Bloqueio de Rede na comunicação com o Groq: {repr(e)}")
    except Exception as e:
        raise Exception(f"Erro Interno da IA (Groq): {repr(e)}")
