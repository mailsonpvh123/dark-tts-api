import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual
from services.ai_service import call_gemini

router = APIRouter(prefix="/api/v1", tags=["Meta & SEO"])

class SeoRequest(BaseModel):
    conteudo: str
    keyword: str
    canal: str

@router.post("/meta-seo")
async def process_seo(
    req: SeoRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    # 1. VALIDAÇÃO DE SESSÃO E SALDO
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    if not req.conteudo:
        raise HTTPException(status_code=400, detail="O roteiro ou conteúdo é obrigatório.")

    # Custo da ferramenta de SEO
    custo_operacao = 15

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Você precisa de {custo_operacao} coins para gerar a arquitetura de SEO.")

    # O Prompt de Elite focado em gabaritar 50/50 no VidIQ
    system_prompt = f"""Você é um mestre em SEO para YouTube e copywriter de canais Dark, especialista em gabaritar a pontuação do VidIQ (50/50). Sua missão é ler o roteiro fornecido e criar 5 PACOTES COMPLETOS de SEO otimizados para o canal '{req.canal}'.

REGRAS ABSOLUTAS DO VIDIQ:
1. CONTAGEM DE TAGS: Você deve fornecer exatas 20 tags.
2. VOLUME DE TAGS (5/5): A maioria das tags deve ter alto volume de busca no YouTube.
3. PALAVRAS-CHAVE NO TÍTULO (5/5): As principais palavras-chave das tags DEVEM estar no Título.
4. PALAVRAS-CHAVE NA DESCRIÇÃO (5/5): As palavras-chave do Título e das Tags DEVEM aparecer naturalmente nos primeiros 2 parágrafos da Descrição.
5. PALAVRAS-CHAVE TRIPLAS (5/5): A palavra-chave principal e as secundárias devem estar presentes, EXATAMENTE IGUAIS, no Título, na Descrição e nas Tags.

O QUE VOCÊ DEVE ENTREGAR:
Gere 5 PACOTES distintos. Cada pacote deve conter:
- TÍTULO: (Clickbait, magnético, usando a palavra-chave principal e respeitando o limite de caracteres).
- DESCRIÇÃO: (2 a 3 parágrafos envolventes usando as tags naturalmente, sem parecer lista. Inclua um Call to Action forte para likes e inscrição).
- TAGS: (Exatas 20 tags separadas por vírgula).

FORMATO DE SAÍDA OBRIGATÓRIO:
Entregue apenas o texto limpo, separado exatamente por estes blocos:

[PACOTE 1]
TÍTULO: 
DESCRIÇÃO: 
TAGS: 

[PACOTE 2]
...
(Vá até o PACOTE 5)"""

    user_content = f"Palavra-chave Foco Sugerida pelo Usuário: {req.keyword}\n\nROTEIRO/CONTEÚDO PARA ANÁLISE:\n{req.conteudo}"

    try:
        resultado = await call_gemini(system_prompt, user_content)
        texto_limpo = resultado.strip()
        
        # ==========================================
        # 2. TRANSAÇÃO FINANCEIRA E HISTÓRICO
        # ==========================================
        usuario.coins -= custo_operacao
        
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Meta & SEO",
            input_usuario=f"Canal: {req.canal} | Keyword: {req.keyword}\nRoteiro: {req.conteudo[:150]}...",
            resultado=texto_limpo, 
            custo_coins=custo_operacao
        )
        
        db.add(novo_historico)
        db.commit()
        
        # Devolvemos o texto e o novo saldo
        return {"status": "sucesso", "seo_result": texto_limpo, "novo_saldo": usuario.coins}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
