import re
import os
import asyncio
import math
import random
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from google import genai
from google.genai import types

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

    try:
        minutos = int(re.search(r'\d+', req.tamanho).group())
    except:
        minutos = 5

    custo_operacao = max(1, minutos)

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para forjar este roteiro de {minutos} minutos.")

    usuario.coins -= custo_operacao
    db.commit()

    try:
        api_key = os.environ.get("GEMINI_API_KEY_FREE") or os.environ.get("GEMINI_API_KEY")
        modelo_texto = os.environ.get("GEMINI_MODEL_TEXT", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("Chave GEMINI_API_KEY_FREE não configurada no servidor.")

        client = genai.Client(api_key=api_key)

        if re.search(r'reddit|porão|medoteca', req.canal, re.IGNORECASE):
            modulo_1_regras = """Regras Específicas para Reddit/Relatos:
- Faça a tradução/adaptação com o mínimo de cortes. Não resuma a essência.
- Mantenha Edits/Coments como 'Atualização 1', 'Atualização 2'. Sem datas.
- Remova nomes de usuários.
- Oculte partes onde o usuário diz não ser o autor original (OP) ou avisos prévios."""
        else:
            modulo_1_regras = """Regras Específicas para Documentário/Mistério/Listas:
- Crie uma narrativa imersiva focada em storytelling cinematográfico.
- REGRAS DE POSIÇÃO (TOP 10): NUNCA inicie tópicos com números secos.
- 🚨 TOLERÂNCIA ZERO PARA METALINGUAGEM: O roteiro é o que o narrador vai falar. Você está TERMINANTEMENTE PROIBIDO de usar expressões como "nesta lista", "vamos listar". APENAS CONTE A HISTÓRIA."""

        template_prompt = ler_prompt_arquivo("script_forge.txt")
        if not template_prompt:
            raise ValueError("O arquivo script_forge.txt sumiu da pasta prompts!")

        prompt_base_formatado = template_prompt.format(
            canal=req.canal if req.canal.strip() else "nosso canal",
            formato=req.formato,
            tamanho=f"{minutos} minutos",
            tom=req.tom,
            instrucoes=req.instrucoes,
            ideia_base=req.ideia_base,
            modulo_1_regras=modulo_1_regras
        )

        print(f"✍️ Iniciando Script Forge (Dinâmico: {minutos} min). Custo: {custo_operacao} Coins.")

        # ==========================================
        # ENGENHARIA ITERATIVA DE ROTEIROS MASSIVOS
        # ==========================================
        texto_limpo = ""
        
        # Cada bloco de geração cobre com precisão cerca de 6 a 7 minutos (aprox. 1000-1200 palavras)
        num_partes = max(1, math.ceil(minutos / 7.0))
        
        if num_partes == 1:
            # ==========================================
            # ROTEIRO CURTO (Geração Padrão em 1 Passagem)
            # ==========================================
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # Implementação assíncrona para não travar a thread do FastAPI
                    response = await client.aio.models.generate_content(
                        model=modelo_texto,
                        contents=prompt_base_formatado,
                        config=types.GenerateContentConfig(temperature=0.7)
                    )
                    texto_limpo = response.text.strip()
                    break
                except Exception as e_api:
                    err_msg = str(e_api).lower()
                    if any(x in err_msg for x in ["503", "429", "unavailable", "demand", "quota", "exhausted", "too many"]):
                        if attempt < max_retries - 1:
                            espera = (10 * (2 ** attempt)) + random.uniform(1, 5)
                            print(f"⚠️ Motor Ocupado/Rate Limit. A aguardar {espera:.1f}s... (Tentativa {attempt+1}/{max_retries})")
                            await asyncio.sleep(espera)
                        else:
                            raise Exception("A Dark Neural Engine está sob tráfego extremo após várias tentativas. Tente novamente.")
                    else:
                        raise e_api
        else:
            # ==========================================
            # ROTEIRO LONGO (Geração em Linha de Montagem)
            # ==========================================
            print(f"🔥 Ativando Forja Iterativa: Quebrando roteiro em {num_partes} partes para atingir o volume massivo!")
            historia_acumulada = ""
            
            for parte_atual in range(1, num_partes + 1):
                print(f"   -> Forjando Parte {parte_atual} de {num_partes}...")
                
                if parte_atual == 1:
                    instrucao_foco = f"ATENÇÃO: Você está escrevendo a PARTE 1 de {num_partes}. Foque APENAS no início da história. É OBRIGATÓRIO incluir o Gancho inicial e as boas-vindas ao canal. NÃO conclua a história de forma alguma."
                elif parte_atual == num_partes:
                    instrucao_foco = f"ATENÇÃO: Você está escrevendo a PARTE FINAL ({num_partes} de {num_partes}). Conclua o desfecho da história de forma magistral e é OBRIGATÓRIO incluir o Call to Action (pedir inscrição/like) na última frase."
                else:
                    instrucao_foco = f"ATENÇÃO: Você está escrevendo o MEIO DA HISTÓRIA (Parte {parte_atual} de {num_partes}). Continue a história com uma riqueza absurda de detalhes, diálogos e tensão emocional. NÃO repita a introdução e NÃO conclua a história."
                
                prompt_iterativo = f"{prompt_base_formatado}\n\n=================================\nINSTRUÇÃO MÁXIMA PARA ESTA ETAPA DE GERAÇÃO:\n{instrucao_foco}\n\nMETA CRÍTICA: Escreva aproximadamente 1000 a 1200 palavras SOMENTE para esta etapa do roteiro."
                
                if historia_acumulada:
                    contexto_continuacao = " ".join(historia_acumulada.split()[-150:])
                    prompt_iterativo += f"\n\nPara garantir a transição perfeita, o último trecho que você escreveu na parte anterior foi:\n'...{contexto_continuacao}'\nContinue a história fluindo naturalmente a partir deste exato ponto."

                max_retries = 5
                texto_parte = ""
                for attempt in range(max_retries):
                    try:
                        # Implementação assíncrona e tempo de temperatura reajustado
                        response = await client.aio.models.generate_content(
                            model=modelo_texto,
                            contents=prompt_iterativo,
                            config=types.GenerateContentConfig(temperature=0.8) 
                        )
                        texto_parte = response.text.strip()
                        break
                    except Exception as e_api:
                        err_msg = str(e_api).lower()
                        # Verificação abrangente de erros de limite e disponibilidade
                        if any(x in err_msg for x in ["503", "429", "unavailable", "demand", "quota", "exhausted", "too many"]):
                            if attempt < max_retries - 1:
                                # Espera progressiva muito maior: ~10s, ~20s, ~40s, ~80s
                                espera = (10 * (2 ** attempt)) + random.uniform(1, 5)
                                print(f"⚠️ Tráfego pesado na IA. Pausa de resfriamento de {espera:.1f}s... (Tentativa {attempt+1}/{max_retries})")
                                await asyncio.sleep(espera)
                            else:
                                raise Exception("O tráfego esmagou a conexão da IA definitivamente. A geração iterativa falhou.")
                        else:
                            raise e_api
                            
                if historia_acumulada:
                    fragmento_final = " ".join(historia_acumulada.split()[-10:])
                    if fragmento_final in texto_parte:
                        texto_parte = texto_parte.replace(fragmento_final, "", 1).strip()
                        
                historia_acumulada += "\n\n" + texto_parte
            
            texto_limpo = historia_acumulada

        # ==========================================
        # LIMPEZA E FORMATAÇÃO FINAL (TEXTO LISO PARA TTS)
        # ==========================================
        # Removemos tudo que for marcação (asteriscos, hashtags, underlines, crases)
        texto_limpo = re.sub(r'[*#_`]', '', texto_limpo)
        # Limpa excesso de pontos e quebras
        texto_limpo = re.sub(r'\.{2,}', '.', texto_limpo)
        # Remove lixo como "Título:", "Parte 1:", "Narrador:" caso a IA tenha inserido
        texto_limpo = re.sub(r'^(?i)(título|parte \d+|capítulo \d+|gancho|narrador):?\s*', '', texto_limpo, flags=re.MULTILINE)
        
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Script Forge",
            input_usuario=f"Canal: {req.canal} | Tempo: {minutos} min",
            resultado=texto_limpo, 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "roteiro": texto_limpo, "novo_saldo": usuario.coins}
        
    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro no Script Forge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
