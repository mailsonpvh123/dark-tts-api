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
# Captura a chave PAGA do Gemini como prioridade máxima. 
# Se ela não existir, tenta o fallback para a GEMINI_API_KEY genérica.
GEMINI_KEY_PAID = os.getenv("GEMINI_API_KEY_PAID", "").strip().strip('"').strip("'")
GEMINI_KEY_GENERICA = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

GEMINI_KEY = GEMINI_KEY_PAID if GEMINI_KEY_PAID else GEMINI_KEY_GENERICA

GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")

if not GEMINI_KEY:
    print("ALERTA CRÍTICO: Chave do Gemini (Paga ou Genérica) não encontrada no ambiente!")
if not GROQ_KEY:
    print("ALERTA CRÍTICO: Chave do Groq não encontrada no ambiente!")
if not OPENAI_KEY:
    print("ALERTA CRÍTICO: Chave da OpenAI não encontrada no ambiente!")

# Inicializa o cliente da nova SDK Oficial do Google (se a chave existir)
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None


# ==========================================
# 2. MOTOR GEMINI (Paraphraser, SEO, Script)
# ==========================================
async def call_gemini(system_prompt, user_content):
    if not client:
        raise Exception("CHAVE API AUSENTE: Configure a GEMINI_API_KEY_PAID no Easypanel.")

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
# 3. MOTOR GROQ (Insights e Roteiros Curtos)
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


# ==========================================
# 4. MOTOR OPENAI (Fallback Roteiros Gigantes)
# ==========================================
async def call_openai_json(system_prompt, user_content):
    if not OPENAI_KEY:
        raise Exception("CHAVE API AUSENTE: Configure a OPENAI_API_KEY no Easypanel.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",  # Modelo de altíssima velocidade, barato e suporta 16k tokens de saída
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.75
    }

    try:
        # Timeout maior garantido para roteiros monstruosos de longos
        async with httpx.AsyncClient(timeout=180.0) as http_client:
            response = await http_client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                data = response.json()
                erro_msg = data.get("error", {}).get("message", "Motivo desconhecido")
                raise Exception(f"OpenAI Recusou [Status {response.status_code}]: {erro_msg}")
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
    except httpx.RequestError as e:
        raise Exception(f"Bloqueio de Rede na comunicação com a OpenAI: {repr(e)}")
    except Exception as e:
        raise Exception(f"Erro Interno da IA (OpenAI): {repr(e)}")
