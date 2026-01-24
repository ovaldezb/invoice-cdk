import json
import mercadopago
import os
import logging

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info("Event received: %s", json.dumps(event))

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST'
    }

    if event['httpMethod'] == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Obtener Access Token de variables de entorno
        access_token = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')
        if not access_token:
            logger.error("MERCADO_PAGO_ACCESS_TOKEN not found in environment")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Internal Server Configuration Error'})
            }

        # Inicializar SDK
        sdk = mercadopago.SDK(access_token)

        # Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # Datos del item a pagar (en el futuro esto podría venir del body o base de datos)
        # Por ahora usamos valores fijos o del body si existen
        title = body.get('title', 'Suscripción Premium')
        quantity = body.get('quantity', 1)
        unit_price = float(body.get('unit_price', 10.0))  # Precio dummy
        
        # Crear preferencia
        preference_data = {
            "items": [
                {
                    "title": title,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "currency_id": "MXN"
                }
            ],
            "back_urls": {
                "success": "http://localhost:4200/dashboard", # TODO: Cambiar por URL real en prod
                "failure": "http://localhost:4200/dashboard",
                "pending": "http://localhost:4200/dashboard"
            },
            "auto_return": "approved"
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]

        logger.info("Preference created: %s", json.dumps(preference))

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'id': preference['id'],
                'init_point': preference['init_point'],
                'sandbox_init_point': preference['sandbox_init_point'] 
            })
        }

    except Exception as e:
        logger.error("Error creating preference: %s", str(e))
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
