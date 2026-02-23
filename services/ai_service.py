import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# 1. Blindagem: Remove espaços ocultos, quebras de linha e aspas acidentais
chave_bruta = os.getenv("GEMINI_API_KEY", "")
GEMINI_KEY = chave_bruta.strip().strip('"').strip("'")

async def call_gemini(system_prompt, user_content):
    if not GEMINI_KEY:
        raise Exception("CHAVE API AUSENTE: O Easypanel não enviou a variável GEMINI_API_KEY para o container.")

    # 2. Blindagem: Usando a versão 2.5-flash definitiva
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_content}]}],
        "generationConfig": {"temperature": 0.75}
    }
    
    try:
        # 3. Blindagem: verify=False ignora erros de certificado desatualizado no AlmaLinux
        # timeout alto (60s) garante que textos gigantes de 3.000 palavras não sejam cortados
        async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
            response = await client.post(url, json=payload)
            
            # Se a comunicação ocorreu, mas o Google barrou (Ex: Chave errada)
            if response.status_code != 200:
                data = response.json()
                erro_msg = data.get("error", {}).get("message", "Motivo desconhecido")
                raise Exception(f"O Google Recusou [Status {response.status_code}]: {erro_msg}")
            
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
            
    except httpx.RequestError as e:
        # O repr(e) vai forçar o Python a cuspir o nome técnico da falha de rede
        raise Exception(f"Bloqueio de Rede no Servidor: {repr(e)}")
    except Exception as e:
        # Qualquer outro erro interno
        raise Exception(f"Erro Interno da IA: {repr(e)}")

# (Seu call_groq futuro pode vir aqui embaixo)
