import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

async def call_gemini(system_prompt, user_content):
    if not GEMINI_KEY:
        raise Exception("CHAVE API AUSENTE: A variável GEMINI_API_KEY não foi encontrada no servidor.")

    # Usando o modelo flash mais estável da API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_content}]}],
        "generationConfig": {"temperature": 0.75}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            data = response.json()
            
            # Se o Google responder com erro (Ex: Chave inválida)
            if response.status_code != 200:
                erro_msg = data.get("error", {}).get("message", "Erro desconhecido da API")
                raise Exception(f"Google API Recusou: {erro_msg}")
                
            return data['candidates'][0]['content']['parts'][0]['text']
            
        except httpx.RequestError as e:
            raise Exception(f"Falha de conexão com o Google: {str(e)}")
        except KeyError:
            raise Exception(f"Resposta inesperada do Google: {data}")

# O call_groq permanece inalterado para quando formos usá-lo
async def call_groq(system_prompt, user_content):
    # ... (mantenha o código do groq aqui caso já tenha colocado)
    pass
