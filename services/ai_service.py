import os
import json
import httpx
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# ==========================================
# 1. TRATAMENTO DE CHAVES E MODELOS
# ==========================================
# Chaves de API
GEMINI_KEY_PAID = os.getenv("GEMINI_API_KEY_PAID", "").strip().strip('"').strip("'")
GEMINI_KEY_GENERICA = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
GEMINI_KEY = GEMINI_KEY_PAID if GEMINI_KEY_PAID else GEMINI_KEY_GENERICA

GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")

# Nomes dos Modelos (Dinâmicos via Easypanel)
MODEL_GEMINI = os.getenv("GEMINI_MODEL_TEXT", "gemini-2.5-flash").strip()
MODEL_GROQ = os.getenv("GROQ_MODEL_TEXT", "llama-3.3-70b-versatile").strip()
MODEL_OPENAI = os.getenv("OPENAI_MODEL_TEXT", "gpt-4o-mini").strip()

if not GEMINI_KEY:
    print("ALERTA CRÍTICO: Chave do Gemini não encontrada!")
if not GROQ_KEY:
    print("ALERTA CRÍTICO: Chave do Groq não encontrada!")
if not OPENAI_KEY:
    print("ALERTA CRÍTICO: Chave da OpenAI não encontrada!")

# Inicializa o cliente do Google
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# ==========================================
# 2. MOTOR GEMINI
# ==========================================
async def call_gemini(system_prompt, user_content):
    if not client:
        raise Exception("CHAVE API AUSENTE: Configure a GEMINI_API_KEY_PAID.")

    try:
        response = await client.aio.models.generate_content(
            model=MODEL_GEMINI,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.75,
            )
        )
        return response.text
    except Exception as e:
        raise Exception(f"Erro na API Google GenAI [{MODEL_GEMINI}]: {str(e)}")

# ==========================================
# 3. MOTOR GROQ
# ==========================================
async def call_groq_json(system_prompt, user_content):
    if not GROQ_KEY:
        raise Exception("CHAVE API AUSENTE: Configure a GROQ_API_KEY.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_GROQ,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            response = await http_client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                data = response.json()
                erro_msg = data.get("error", {}).get("message", "Motivo desconhecido")
                raise Exception(f"Groq Recusou [{MODEL_GROQ}]: {erro_msg}")
            
            data = response.json()
            return data['choices'][0]['message']['content']
    except Exception as e:
        raise Exception(f"Erro Interno Groq: {repr(e)}")

# ==========================================
# 4. MOTOR OPENAI
# ==========================================
async def call_openai_json(system_prompt, user_content):
    if not OPENAI_KEY:
        raise Exception("CHAVE API AUSENTE: Configure a OPENAI_API_KEY.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_OPENAI,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.75
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as http_client:
            response = await http_client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                data = response.json()
                erro_msg = data.get("error", {}).get("message", "Motivo desconhecido")
                raise Exception(f"OpenAI Recusou [{MODEL_OPENAI}]: {erro_msg}")
            
            data = response.json()
            return data['choices'][0]['message']['content']
    except Exception as e:
        raise Exception(f"Erro Interno OpenAI: {repr(e)}")
