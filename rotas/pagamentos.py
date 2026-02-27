import mercadopago
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Nossos imports internos
import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1/pagamentos", tags=["Pagamentos"])

# ==========================================
# CONFIGURAÇÕES DO MERCADO PAGO
# ==========================================
MP_ACCESS_TOKEN = "APP_USR-3763574332833219-080715-441c2d79367de336c403fd1c6ab2f82a-1220264860"
DOMINIO_WEBHOOK = "https://suite.zappclube.com.br" # Coloque o seu domínio real aqui com HTTPS

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# ==========================================
# TABELA DE PREÇOS E PACOTES
# ==========================================
PACOTES = {
    "basic": {"nome": "Plano Basic", "valor": 75.00, "coins": 3000, "plano_id": "BASIC"},
    "plus": {"nome": "Plano Plus", "valor": 150.00, "coins": 6000, "plano_id": "PLUS"},
    "pro": {"nome": "Plano Pro", "valor": 300.00, "coins": 12000, "plano_id": "PRO"},
    "avulso_1000": {"nome": "Pacote Avulso 1.000 Coins", "valor": 25.00, "coins": 1000, "plano_id": "MANTER"},
    "avulso_2000": {"nome": "Pacote Avulso 2.000 Coins", "valor": 50.00, "coins": 2000, "plano_id": "MANTER"},
    "avulso_4000": {"nome": "Pacote Avulso 4.000 Coins", "valor": 100.00, "coins": 4000, "plano_id": "MANTER"}
}

class PagamentoRequest(BaseModel):
    pacote: str

@router.post("/gerar-pix")
async def gerar_pix(
    req: PagamentoRequest,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada.")

    if req.pacote not in PACOTES:
        raise HTTPException(status_code=400, detail="Pacote inválido.")

    pacote_info = PACOTES[req.pacote]

    # Criamos uma referência externa injetando os dados que precisamos recuperar no webhook
    referencia_externa = f"UID:{usuario.id}|COINS:{pacote_info['coins']}|PLANO:{pacote_info['plano_id']}"

    payment_data = {
        "transaction_amount": pacote_info["valor"],
        "description": f"Dark Creator OS - {pacote_info['nome']}",
        "payment_method_id": "pix",
        "payer": {
            "email": usuario.email,
            "first_name": usuario.email.split('@')[0]
        },
        "external_reference": referencia_externa,
        "notification_url": f"{DOMINIO_WEBHOOK}/api/v1/pagamentos/webhook"
    }

    try:
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response["response"]

        if "id" not in payment:
            raise Exception("Erro ao gerar PIX no Mercado Pago.")

        qr_code_base64 = payment["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        qr_code_copia_cola = payment["point_of_interaction"]["transaction_data"]["qr_code"]
        payment_id = payment["id"]

        return {
            "status": "sucesso",
            "payment_id": payment_id,
            "qr_code_base64": qr_code_base64,
            "qr_code": qr_code_copia_cola
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def mercado_pago_webhook(request: Request, db: Session = Depends(get_db)):
    """Rota que o Mercado Pago chama quando o Pix é pago."""
    try:
        data = await request.json()
        
        # O MP manda o ID do pagamento dentro de data.data.id ou data.id dependendo do evento
        payment_id = None
        if "data" in data and "id" in data["data"]:
            payment_id = data["data"]["id"]
        elif "id" in data:
            payment_id = data["id"]
            
        if not payment_id:
            return {"status": "ignorado", "motivo": "Sem ID de pagamento"}

        # Consulta o status real do pagamento no MP por segurança
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] != 200:
            return {"status": "erro", "motivo": "Pagamento não encontrado"}

        payment = payment_info["response"]
        
        # Se o pagamento foi aprovado, vamos entregar as moedas!
        if payment["status"] == "approved":
            referencia = payment.get("external_reference", "")
            
            if "UID:" in referencia:
                # Quebrando a string: UID:1|COINS:3000|PLANO:BASIC
                partes = referencia.split("|")
                user_id = int(partes[0].split(":")[1])
                moedas_compradas = int(partes[1].split(":")[1])
                novo_plano = partes[2].split(":")[1]

                usuario = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
                if usuario:
                    # Adiciona as moedas
                    usuario.coins += moedas_compradas
                    
                    # Atualiza o plano (se não for pacote avulso)
                    if novo_plano != "MANTER":
                        usuario.tipo_plano = novo_plano
                        
                    db.commit()
                    print(f"💰 Venda Concluída! {moedas_compradas} Coins entregues para {usuario.email}.")

        return {"status": "sucesso"}

    except Exception as e:
        print(f"❌ Erro no Webhook: {e}")
        return {"status": "erro"}
