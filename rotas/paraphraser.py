import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1/paraphraser", tags=["Paraphraser"])

class ParaphraseRequest(BaseModel):
    texto: str
    tom: str = "Sarcástico e Ácido"
    idioma: str = "Português (Brasil)"
    modo: str = "padrao"         # Novo: 'padrao' ou 'reddit'
    gancho_exato: str = ""       # Novo: Título exato para iniciar o roteiro

def ler_prompt_arquivo(nome_arquivo: str) -> str:
    """Lê o conteúdo de um arquivo de prompt na pasta 'prompts'."""
    caminho = os.path.join(os.getcwd(), "prompts", nome_arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"⚠️ Aviso: Arquivo de prompt {nome_arquivo} não encontrado. Usando fallback. Erro: {e}")
        return "Você é um roteirista profissional. Reescreva o texto mantendo a essência, mas com alta originalidade e formatação limpa."

@router.post("/")
async def gerar_parafraze(
    req: ParaphraseRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")
        
    texto_original = req.texto.strip()
    if not texto_original:
        raise HTTPException(status_code=400, detail="O texto original não pode estar vazio.")

    custo_operacao = 15

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para reescrever.")

    usuario.coins -= custo_operacao
    db.commit()

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Chave GEMINI_API_KEY não configurada no servidor.")

        client = genai.Client(api_key=api_key)

        # 1. Carrega o System Prompt dinamicamente do arquivo correto
        if req.modo == "reddit":
            instrucao_sistema = ler_prompt_arquivo("reddit_mode.txt")
        else:
            # Caso o usuário esteja usando a ferramenta para roteiros normais
            # Você pode criar um 'padrao_mode.txt' depois, por enquanto deixamos um texto base
            instrucao_sistema = (
                "Você é um roteirista de elite. Reescreva o texto garantindo 100% de originalidade "
                "para evitar detecção de plágio, mas mantendo a essência e os fatos. "
                "Adapte o vocabulário para ser lido em voz alta de forma natural por um locutor."
            )

        # 2. Constrói o Prompt de Comando do Usuário
        prompt_linhas = []
        prompt_linhas.append(f"Reescreva e adapte o texto abaixo no idioma '{req.idioma}'.")
        prompt_linhas.append(f"Aplique estritamente o tom de voz: {req.tom}.")
        
        # Injeta o Gancho Exato, se o usuário forneceu
        if req.gancho_exato.strip():
            prompt_linhas.append(f"\nATENÇÃO: Inicie o roteiro OBRIGATORIAMENTE com esta exata frase/título: \"{req.gancho_exato.strip()}\". Não mude nenhuma palavra deste gancho inicial.")
            
        prompt_linhas.append(f"\nTexto original:\n{texto_original}")
        
        prompt_final = "\n".join(prompt_linhas)

        # 3. Dispara para o Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_final,
            config=types.GenerateContentConfig(
                system_instruction=instrucao_sistema,
                temperature=0.7 
            )
        )
        
        texto_gerado = response.text

        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta=f"Paraphraser ({req.modo.upper()})",
            input_usuario=f"Tom: {req.tom} | Gancho: {req.gancho_exato}\nTexto: {texto_original[:100]}...",
            resultado=texto_gerado[:150] + "...", 
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {
            "status": "sucesso", 
            "texto_parafrazedo": texto_gerado, 
            "novo_saldo": usuario.coins
        }

    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no Paraphraser: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na Inteligência Artificial. Os seus {custo_operacao} coins foram estornados. Tente novamente.")
