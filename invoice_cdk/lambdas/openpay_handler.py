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
    logger.info("OpenPay Event received (Payload Fix): %s", json.dumps(event))

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
        merchant_id = os.environ.get('OPENPAY_MERCHANT_ID', '').strip()
        private_key = os.environ.get('OPENPAY_PRIVATE_KEY', '').strip()
        production_mode_str = os.environ.get('OPENPAY_PRODUCTION_MODE', 'false').lower().strip()
        production_mode = production_mode_str == 'true'

        if not all([merchant_id, private_key]):
            logger.error("Missing OpenPay credentials in environment")
            return {
                'statusCode': 500,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Internal Server Configuration Error: Missing Credentials'})
            }

        # Determinar base URL
        base_url = "https://api.openpay.mx/v1" if production_mode else "https://sandbox-api.openpay.mx/v1"
        endpoint = f"{base_url}/{merchant_id}/checkouts"

        # Parsear body
        body = json.loads(event.get('body', '{}'))
        
        title = body.get('title', 'Pago de Servicios')
        amount_val = float(body.get('unit_price', 0.0))
        
        if amount_val <= 0:
             return {
                'statusCode': 400,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Invalid amount'})
            }

        # IMPORTANTE: Amount debe ser STRING con 2 decimales
        amount_str = "{:.2f}".format(amount_val)

        # Preparar payload para Checkout (Basado en documentacion oficial de Checkout)
        customer_body = body.get('customer', {})
        
        # Combinar datos por defecto con lo que venga en el body
        customer_data = {
            "name": customer_body.get("name", "Cliente Inmobiliaria"),
            "last_name": customer_body.get("last_name", "Residente"),
            "phone_number": customer_body.get("phone_number", "5512345678"),
            "email": customer_body.get("email", "pago@cliente.com")
        }

        checkout_data = {
            "amount": amount_str,
            "currency": "MXN",
            "description": title,
            "order_id": f"ORD-{os.urandom(4).hex().upper()}",
            "redirect_url": f"{origin}/dashboard" if origin else "http://localhost:4200/dashboard",
            "send_email": "false", # Como string
            "customer": customer_data
        }

        logger.info("Calling OpenPay API: %s with customer: %s", endpoint, customer_data)

        # Realizar peticion con Requests y Basic Auth
        response = requests.post(
            endpoint,
            json=checkout_data,
            auth=HTTPBasicAuth(private_key, ''),
            headers={'Content-Type': 'application/json'},
            timeout=15
        )

        logger.info("OpenPay API Response Status: %s", response.status_code)
        
        if response.status_code not in [200, 201]:
            logger.error("OpenPay error response (1001 fix attempt): %s", response.text)
            return {
                'statusCode': response.status_code,
                'headers': headers_cors,
                'body': response.text
            }

        result = response.json()
        
        return {
            'statusCode': 200,
            'headers': headers_cors,
            'body': json.dumps({
                'id': result.get('id'),
                'checkout_url': result.get('checkout_link')
            })
        }

    except Exception as e:
        logger.error("Unexpected error in OpenPay handler: %s", str(e))
        return {
            'statusCode': 500,
            'headers': headers_cors,
            'body': json.dumps({'error': str(e)})
        }
