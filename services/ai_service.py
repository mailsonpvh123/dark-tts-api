import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

async def call_gemini(system_prompt, user_content):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_content}]}],
        "generationConfig": {"temperature": 0.75}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=60.0)
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']

async def call_groq(system_prompt, user_content):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "response_format": {"type": "json_object"}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        data = response.json()
        return data['choices'][0]['message']['content']
