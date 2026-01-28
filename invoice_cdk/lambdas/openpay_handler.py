import json
import os
import logging
import requests
from requests.auth import HTTPBasicAuth
from utils import valida_cors
from constantes import Constants

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("OpenPay Event received (Requests version): %s", json.dumps(event))

    headers_incoming = event.get("headers", {})
    origin = headers_incoming.get("origin") or headers_incoming.get("Origin")
    
    headers_cors = Constants.HEADERS.copy()
    headers_cors["Access-Control-Allow-Origin"] = valida_cors(origin)

    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers_cors,
            'body': ''
        }
    
    try:
        # Configurar OpenPay credentials
        merchant_id = os.environ.get('OPENPAY_MERCHANT_ID')
        private_key = os.environ.get('OPENPAY_PRIVATE_KEY')
        production_mode = os.environ.get('OPENPAY_PRODUCTION_MODE', 'false').lower() == 'true'

        if not all([merchant_id, private_key]):
            logger.error("OpenPay credentials not found in environment")
            return {
                'statusCode': 500,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Internal Server Configuration Error'})
            }

        # Determinar base URL
        base_url = "https://api.openpay.mx/v1" if production_mode else "https://sandbox-api.openpay.mx/v1"
        endpoint = f"{base_url}/{merchant_id}/checkouts"

        # Parsear body
        body = json.loads(event.get('body', '{}'))
        
        title = body.get('title', 'Pago de Servicios')
        amount = float(body.get('unit_price', 0.0))
        
        if amount <= 0:
             return {
                'statusCode': 400,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Invalid amount'})
            }

        # Preparar payload para Checkout
        checkout_data = {
            "method": "card",
            "amount": amount,
            "description": title,
            "order_id": f"ORD-{os.urandom(4).hex().upper()}",
            "currency": "MXN",
            "redirect_url": f"{origin}/dashboard" if origin else "http://localhost:4200/dashboard",
            "send_email": False
        }

        logger.info("Calling OpenPay API: %s with data: %s", endpoint, json.dumps(checkout_data))

        # Realizar peticion con Requests y Basic Auth
        # Auth: User = PrivateKey, Password = (empty)
        response = requests.post(
            endpoint,
            json=checkout_data,
            auth=HTTPBasicAuth(private_key, ''),
            headers={'Content-Type': 'application/json'}
        )

        logger.info("OpenPay API Response Status: %s", response.status_code)
        
        if response.status_code not in [200, 201]:
            logger.error("OpenPay error response: %s", response.text)
            return {
                'statusCode': response.status_code,
                'headers': headers_cors,
                'body': response.text
            }

        result = response.json()
        
        # OpenPay devuelve 'id' y 'checkout_link' para el objeto checkout
        return {
            'statusCode': 200,
            'headers': headers_cors,
            'body': json.dumps({
                'id': result.get('id'),
                'checkout_url': result.get('checkout_link')
            })
        }

    except Exception as e:
        logger.error("Error in OpenPay handler: %s", str(e))
        return {
            'statusCode': 500,
            'headers': headers_cors,
            'body': json.dumps({'error': str(e)})
        }
