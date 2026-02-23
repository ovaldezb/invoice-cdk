import json
import os
import logging
import requests
import base64
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
        clip_secret_key = os.environ.get('CLIP_SECRET_KEY', '').strip()
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
        base_url = "https://api.payclip.com"
        endpoint = f"{base_url}/payments"

        # Parsear body
        body = json.loads(event.get('body', '{}'))
        
        title = body.get('title', 'Pago de Servicios')
        amount_val = float(body.get('unit_price', 0.0))
        card_token_id = body.get('card_token_id')
        
        if amount_val <= 0:
             return {
                'statusCode': 400,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Invalid amount'})
            }

        if not card_token_id:
             return {
                'statusCode': 400,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Missing card_token_id'})
            }

        customer_body = body.get('customer', {})
        customer_email = customer_body.get('email', 'pago@cliente.com')
        customer_phone = customer_body.get('phone_number', '5555555555')

        # Preparar payload para Pago Transparente de Clip
        payment_data = {
            "amount": round(amount_val, 2),
            "currency": "MXN",
            "description": title,
            "payment_method": {
                "token": card_token_id
            },
            "customer": {
                "email": customer_email,
                "phone": customer_phone
            }
        }

        logger.info("Calling Clip Payments API: %s", endpoint)

        # Realizar peticion con Requests y Auth Bearer (o Basic segun doc de clip, asumo HTTP Basic para server a server o token bearer)
        # Segun https://developer.clip.mx/reference/createnewpaymentlink, usa Basic auth con x-api-key en header un token en auth
        # Actually standard clip uses Basic auth o Header x-api-key o Bearer dependiendo. As lets set x-api-key o Authorization
        # Generar Token Basic a partir de Key y Secret
        credentials = f"{clip_api_key}:{clip_secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            "accept": "application/vnd.com.payclip.v2+json",
            "content-type": "application/json",
            "Authorization": f"Basic {encoded_credentials}"
        }

        response = requests.post(
            endpoint,
            json=payment_data,
            headers=headers,
            timeout=25
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
        
        status = result.get('status', '')
        internal_status = 'pending'
        if status == 'APPROVED':
            internal_status = 'approved'
        elif status in ['DECLINED', 'CANCELLED', 'ERROR', 'FAILED']:
            internal_status = 'rejected'
            
        # Intentar insertar en MongoDB directamente para respuesta sincrona
        try:
            from db import get_db_collection
            import datetime
            collection = get_db_collection()
            if collection is not None:
                payment_record = {
                    'provider': 'CLIP',
                    'status': internal_status,
                    'transaction_amount': amount_val,
                    'date_created': datetime.datetime.utcnow().isoformat() + "Z",
                    'original_payload': result,
                    'receipt_no': result.get('receipt_no', '')
                }
                collection.insert_one(payment_record)
        except Exception as e:
            logger.error("Could not insert payment into MongoDB: %s", str(e))
        
        return {
            'statusCode': 200,
            'headers': headers_cors,
            'body': json.dumps({
                'id': result.get('id', result.get('payment_request_id')),
                'status': internal_status,
                'receipt_no': result.get('receipt_no'),
                'clip_response': result
            })
        }

    except Exception as e:
        logger.error("Unexpected error in Clip handler: %s", str(e))
        return {
            'statusCode': 500,
            'headers': headers_cors,
            'body': json.dumps({'error': str(e)})
        }
