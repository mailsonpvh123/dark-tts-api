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
    modo: str = "padrao"         
    gancho_exato: str = ""       
    nome_canal: str = ""         

def ler_prompt_arquivo(nome_arquivo: str) -> str:
    caminho = os.path.join(os.getcwd(), "prompts", nome_arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado. Usando fallback.")
        return "Você é um roteirista profissional. Reescreva o texto mantendo a essência, mas com alta originalidade e formatação limpa."

@router.post("")
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

    custo_operacao = 25 

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para reescrever.")

    usuario.coins -= custo_operacao
    db.commit()

    try:
        # ==========================================
        # ROTEAMENTO INTELIGENTE (CHAVE FREE E MODELO DINÂMICO)
        # ==========================================
        api_key = os.environ.get("GEMINI_API_KEY_FREE") or os.environ.get("GEMINI_API_KEY")
        modelo_texto = os.environ.get("GEMINI_MODEL_TEXT", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("Chave GEMINI_API_KEY_FREE não configurada no servidor.")

        client = genai.Client(api_key=api_key)

        if req.modo == "reddit":
            instrucao_sistema = ler_prompt_arquivo("reddit_mode.txt")
        else:
            instrucao_sistema = ler_prompt_arquivo("padrao_mode.txt")

        # CONTAGEM E TRAVA DE VOLUME
        qtd_palavras_originais = len(texto_original.split())

        prompt_linhas = []
        prompt_linhas.append(f"Reescreva e adapte o texto abaixo no idioma '{req.idioma}'.")
        prompt_linhas.append(f"Aplique estritamente o tom de voz: {req.tom}.")
        
        # Arma apontada para a Preguiça Neural
        prompt_linhas.append(f"\n🚨 REGRA DE OURO DO TAMANHO: O texto original contém {qtd_palavras_originais} palavras. O seu roteiro final reescrito DEVE TER NO MÍNIMO essa mesma quantidade de palavras ou ser ainda maior. NUNCA RESUMA. Se remover lixo do texto original, expanda a história com descrições e roteirização rica para compensar o tamanho.")
        
        if req.nome_canal.strip():
            prompt_linhas.append(f"O nome do canal é '{req.nome_canal.strip()}'. Adapte os CTAs de introdução e encerramento citando este nome de forma orgânica.")

        if req.gancho_exato.strip():
            prompt_linhas.append(f"\nATENÇÃO: Inicie o roteiro OBRIGATORIAMENTE com esta exata frase/título: \"{req.gancho_exato.strip()}\". Não mude nenhuma palavra deste gancho inicial.")
            
        prompt_linhas.append(f"\nTexto original:\n{texto_original}")
        prompt_final = "\n".join(prompt_linhas)

        print(f"✍️ Iniciando Paraphraser (Modelo: {modelo_texto} | Chave: FREE | Alvo: {qtd_palavras_originais}+ palavras). Custo: {custo_operacao} Coins.")

        response = client.models.generate_content(
            model=modelo_texto,
            contents=prompt_final,
            config=types.GenerateContentConfig(
                system_instruction=instrucao_sistema,
                temperature=0.8 # Aumentei um pouco para dar mais criatividade na expansão
            )
        )
        
        texto_gerado = response.text.strip()

        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta=f"Paraphraser ({req.modo.upper()})",
            input_usuario=f"Canal: {req.nome_canal} | Gancho: {req.gancho_exato}\nTexto Original: {texto_original[:100]}...",
            resultado=texto_gerado, 
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
        raise HTTPException(status_code=500, detail=f"Falha na IA. Os seus {custo_operacao} coins foram estornados. Erro: {str(e)}")
