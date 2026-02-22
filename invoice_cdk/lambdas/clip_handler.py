import json
import os
import logging
import requests
from utils import valida_cors
from constantes import Constants

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("Clip Event received: %s", json.dumps(event))

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
        # Configurar Clip credentials
        clip_api_key = os.environ.get('CLIP_API_KEY', '').strip()
        production_mode_str = os.environ.get('CLIP_PRODUCTION_MODE', 'false').lower().strip()
        production_mode = production_mode_str == 'true'

        if not clip_api_key:
            logger.error("Missing Clip credentials in environment")
            return {
                'statusCode': 500,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Internal Server Configuration Error: Missing Credentials'})
            }

        # Determinar base URL
        # Clip uses https://api.payclip.com for both prod and sandbox. The API KEY determines the environment.
        base_url = "https://api.payclip.com"
        endpoint = f"{base_url}/checkout"

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

        customer_body = body.get('customer', {})
        customer_email = customer_body.get('email', 'pago@cliente.com')

        # Build dynamic webhook url
        domain_name = event.get('requestContext', {}).get('domainName', '')
        path = event.get('requestContext', {}).get('path', '/clip/create-checkout')
        webhook_path = path.replace('/create-checkout', '/webhook')
        webhook_url = f"https://{domain_name}{webhook_path}" if domain_name else ""

        # Preparar payload para Checkout de Clip
        checkout_data = {
            "amount": round(amount_val, 2),
            "currency": "MXN",
            "purchase_description": title,
            "redirection_url": {
                "success": f"{origin}/dashboard" if origin else "http://localhost:4200/dashboard",
                "error": f"{origin}/dashboard" if origin else "http://localhost:4200/dashboard",
                "default": f"{origin}/dashboard" if origin else "http://localhost:4200/dashboard"
            },
            "webhook_url": webhook_url,
            "metadata": {
                "custom_info": f"Invoice Payment for {customer_email}"
            }
        }

        logger.info("Calling Clip API: %s", endpoint)

        # Realizar peticion con Requests y Auth Bearer (o Basic segun doc de clip, asumo HTTP Basic para server a server o token bearer)
        # Segun https://developer.clip.mx/reference/createnewpaymentlink, usa Basic auth con x-api-key en header un token en auth
        # Actually standard clip uses Basic auth o Header x-api-key o Bearer dependiendo. As lets set x-api-key o Authorization
        
        headers = {
            "accept": "application/vnd.com.payclip.v2+json",
            "content-type": "application/json",
            "x-api-key": clip_api_key
        }

        response = requests.post(
            endpoint,
            json=checkout_data,
            headers=headers,
            timeout=15
        )

        logger.info("Clip API Response Status: %s", response.status_code)
        
        if response.status_code not in [200, 201]:
            logger.error("Clip error response: %s", response.text)
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
                'id': result.get('payment_request_id'),
                'checkout_url': result.get('payment_request_url')
            })
        }

    except Exception as e:
        logger.error("Unexpected error in Clip handler: %s", str(e))
        return {
            'statusCode': 500,
            'headers': headers_cors,
            'body': json.dumps({'error': str(e)})
        }
