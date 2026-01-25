import json
import os
import mercadopago
from pymongo import MongoClient
import logging

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurar MongoDB
client = MongoClient(os.environ['MONGODB_URI'])
db = client[os.environ['DB_NAME']]
payments_collection = db['payments']

def handler(event, context):
    logger.info("Webhook Event received: %s", json.dumps(event))

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }

    if event['httpMethod'] == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    try:
        # 1. Validar Token
        access_token = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')
        if not access_token:
            logger.error("Missing MERCADO_PAGO_ACCESS_TOKEN")
            return {'statusCode': 500, 'headers': headers, 'body': 'Server Error'}

        sdk = mercadopago.SDK(access_token)
        
        # 2. Parsear Notificación
        # Mercado Pago envía parámetros en el query string para Webhooks tipo "topic" o "type"
        # Ojo: La nueva versión de Webhooks envía un body JSON.
        # Vamos a soportar ambos por robustez, pero priorizamos el body.
        
        body = json.loads(event.get('body', '{}'))
        query_params = event.get('queryStringParameters') or {}
        
        topic = body.get('topic') or body.get('type') or query_params.get('topic') or query_params.get('type')
        resource_id = body.get('data', {}).get('id') or query_params.get('id')

        logger.info(f"Processing Topic: {topic}, ID: {resource_id}")

        if topic == 'payment':
            if not resource_id:
                logger.warning("Payment Notification without ID")
                return {'statusCode': 200, 'headers': headers, 'body': 'OK'}

            # 3. Consultar Estado del Pago a Mercado Pago
            # Nunca confíes solo en la data del webhook, consulta la fuente de verdad.
            payment_info = sdk.payment().get(resource_id)
            payment = payment_info.get("response", {})
            
            if not payment:
                logger.error(f"Payment {resource_id} not found in MP")
                return {'statusCode': 200, 'headers': headers, 'body': 'Payment not found'}

            logger.info("Payment Fetched: %s", json.dumps(payment))

            # 4. Guardar en Base de Datos
            # Usamos update_one con upsert=True para guardar o actualizar
            payment_data = {
                "_id": str(payment.get("id")), # ID de MP como _id
                "status": payment.get("status"),
                "status_detail": payment.get("status_detail"),
                "transaction_amount": payment.get("transaction_amount"),
                "date_created": payment.get("date_created"),
                "date_approved": payment.get("date_approved"),
                "payment_method_id": payment.get("payment_method_id"),
                "payment_type_id": payment.get("payment_type_id"),
                "payer": payment.get("payer"),
                "external_reference": payment.get("external_reference"), # Aquí vendrá el ID de tu usuario/factura
                "last_updated": os.environ.get("aws_request_id") # Marker de actualización
            }

            payments_collection.update_one(
                {"_id": payment_data["_id"]},
                {"$set": payment_data},
                upsert=True
            )
            
            logger.info(f"Payment {resource_id} saved/updated successfully")

        return {'statusCode': 200, 'headers': headers, 'body': 'OK'}

    except Exception as e:
        logger.error("Error processing webhook: %s", str(e))
        # Retornamos 200 para que MP no reintente infinitamente si es un error lógico nuestro
        return {'statusCode': 200, 'headers': headers, 'body': 'Error'}
