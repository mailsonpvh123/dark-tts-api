import re
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Script Forge"])

class ScriptRequest(BaseModel):
    ideia_base: str
    canal: str
    formato: str
    tamanho: str
    tom: str
    instrucoes: str

def ler_prompt_arquivo(nome_arquivo: str) -> str:
    caminho = os.path.join(os.getcwd(), "prompts", nome_arquivo)
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"⚠️ Aviso: Arquivo {nome_arquivo} não encontrado na pasta prompts!")
        return ""

@router.post("/script-forge")
async def process_script(
    req: ScriptRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.ideia_base:
        raise HTTPException(status_code=400, detail="A ideia base é obrigatória.")

    # Custo do Roteiro
    custo_operacao = 25

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para forjar este roteiro.")

    # Débito Antecipado
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

        # Define as regras condicionais
        if re.search(r'reddit|porão|medoteca', req.canal, re.IGNORECASE):
            modulo_1_regras = """Regras Específicas para Reddit/Relatos:
- Faça a tradução/adaptação com o mínimo de cortes. Não resuma a essência.
- Mantenha Edits/Coments como 'Atualização 1', 'Atualização 2'. Sem datas.
- Remova nomes de usuários.
- Oculte partes onde o usuário diz não ser o autor original (OP) ou avisos prévios."""
        else:
            modulo_1_regras = """Regras Específicas para Documentário/Mistério/Listas:
- Crie uma narrativa imersiva focada em storytelling cinematográfico.
- REGRAS DE POSIÇÃO (TOP 10): NUNCA inicie tópicos com números secos (ex: '10.', '9. O Caso'). Use texto corrido: 'Em décimo lugar, temos...', 'Ocupando a nona posição...'.
- 🚨 TOLERÂNCIA ZERO PARA METALINGUAGEM: O roteiro é o que o narrador vai falar. Você está TERMINANTEMENTE PROIBIDO de usar expressões como "nesta contagem regressiva", "nesta lista", "vamos listar", ou "em ordem decrescente". Não avise o espectador sobre a estrutura mecânica do vídeo, APENAS CONTE A HISTÓRIA."""

        # Lê o Template do Prompt
        template_prompt = ler_prompt_arquivo("script_forge.txt")
        if not template_prompt:
            raise ValueError("O arquivo script_forge.txt sumiu da pasta prompts!")

        # Mágica de injeção de variáveis no texto
        prompt_final = template_prompt.format(
            canal=req.canal if req.canal.strip() else "nosso canal",
            formato=req.formato,
            tamanho=req.tamanho,
            tom=req.tom,
            instrucoes=req.instrucoes,
            ideia_base=req.ideia_base,
            modulo_1_regras=modulo_1_regras
        )

        print(f"✍️ Iniciando Script Forge (Modelo: {modelo_texto} | Chave: FREE). Custo: {custo_operacao} Coins.")

        response = client.models.generate_content(
            model=modelo_texto,
            contents=prompt_final,
            config=types.GenerateContentConfig(
                temperature=0.7 
            )
        )
        
        texto_limpo = response.text.strip()
        
        # Limpeza fina para o Voice Synthesizer
        texto_limpo = texto_limpo.replace('*', '').replace('#', '')
        # AQUI FOI REMOVIDA A DESTRUIÇÃO DE INTERROGAÇÕES E EXCLAMAÇÕES!
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        
        # Gravamos o Roteiro Inteiro (texto_limpo) no Histórico
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Script Forge",
            input_usuario=f"Canal: {req.canal} | Modelo: {modelo_texto}",
            resultado=texto_limpo, 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "roteiro": texto_limpo, "novo_saldo": usuario.coins}
        
    except Exception as e:
        # Reembolso em caso de falha da IA
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no Script Forge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
