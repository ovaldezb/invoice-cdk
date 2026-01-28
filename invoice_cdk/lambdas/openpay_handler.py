import json
import openpay
import os
import logging
from utils import valida_cors
from constantes import Constants

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("OpenPay Event received: %s", json.dumps(event))

    headers_incoming = event.get("headers", {})
    origin = headers_incoming.get("origin") or headers_incoming.get("Origin")
    
    headers = Constants.HEADERS.copy()
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)

    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Configurar OpenPay
        merchant_id = os.environ.get('OPENPAY_MERCHANT_ID')
        public_key = os.environ.get('OPENPAY_PUBLIC_KEY')
        private_key = os.environ.get('OPENPAY_PRIVATE_KEY')
        production_mode = os.environ.get('OPENPAY_PRODUCTION_MODE', 'false').lower() == 'true'

        if not all([merchant_id, public_key, private_key]):
            logger.error("OpenPay credentials not found in environment")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Internal Server Configuration Error'})
            }

        openpay.merchant_id = merchant_id
        openpay.public_key = public_key
        openpay.private_key = private_key
        openpay.production_mode = production_mode

        # Parsear body
        body = json.loads(event.get('body', '{}'))
        
        title = body.get('title', 'Pago de Servicios')
        amount = float(body.get('unit_price', 0.0))
        
        if amount <= 0:
             return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid amount'})
            }

        # Crear transaccion de checkout
        # Referencia: https://www.openpay.mx integraciones checkout
        
        checkout_data = {
            "method": "card",
            "amount": amount,
            "description": title,
            "order_id": f"ORD-{os.urandom(4).hex().upper()}", # Generar un ID unico
            "currency": "MXN",
            "redirect_url": f"{origin}/dashboard" if origin else "http://localhost:4200/dashboard",
        }

        logger.info("Creating OpenPay checkout with data: %s", json.dumps(checkout_data))

        # Nota: La SDK de OpenPay para Python puede variar segun la version.
        # Basado en la documentacion para Checkout:
        checkout = openpay.Checkout.create(**checkout_data)
        
        logger.info("OpenPay checkout created: %s", checkout.id)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'id': checkout.id,
                'checkout_url': checkout.checkout_link
            })
        }

    except Exception as e:
        logger.error("Error creating OpenPay checkout: %s", str(e))
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
