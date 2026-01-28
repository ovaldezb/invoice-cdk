import json
import os
import logging
from pymongo import MongoClient
from utils import valida_cors
from constantes import Constants

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurar MongoDB
client = MongoClient(os.environ['MONGODB_URI'])
db = client[os.environ['DB_NAME']]
payments_collection = db['payments']

def handler(event, context):
    logger.info("OpenPay Webhook Event received: %s", json.dumps(event))

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
        # Parsear body
        body = json.loads(event.get('body', '{}'))
        event_type = body.get('type')
        
        # 1. Manejar Verificación Inicial de OpenPay
        # Cuando se registra el webhook, OpenPay envía un POST con un verification_code
        if 'verification_code' in body:
            verification_code = body.get('verification_code')
            logger.info(f"OpenPay Verification Code received: {verification_code}")
            return {
                'statusCode': 200,
                'headers': headers_cors,
                'body': json.dumps({'verification_code': verification_code})
            }

        # 2. Manejar Evento de Pago Exitoso
        if event_type == 'charge.succeeded':
            transaction = body.get('transaction', {})
            transaction_id = transaction.get('id')
            
            if not transaction_id:
                logger.warning("Charge notification without transaction ID")
                return {'statusCode': 200, 'headers': headers_cors, 'body': 'OK'}

            logger.info(f"Processing successful payment: {transaction_id}")

            # Mapear datos al formato de nuestra colección 'payments'
            payment_data = {
                "_id": str(transaction_id), # ID de OpenPay como _id
                "provider": "openpay",
                "status": transaction.get("status"),
                "transaction_amount": float(transaction.get("amount", 0)),
                "date_created": transaction.get("creation_date"),
                "date_approved": transaction.get("operation_date"),
                "description": transaction.get("description"),
                "order_id": transaction.get("order_id"),
                "currency": transaction.get("currency"),
                "method": transaction.get("method"),
                "customer": transaction.get("customer"),
                "last_updated": context.aws_request_id if context else "manual"
            }

            # Guardar o actualizar en MongoDB
            payments_collection.update_one(
                {"_id": payment_data["_id"]},
                {"$set": payment_data},
                upsert=True
            )
            
            logger.info(f"OpenPay Payment {transaction_id} saved/updated successfully")

        return {
            'statusCode': 200,
            'headers': headers_cors,
            'body': 'OK'
        }

    except Exception as e:
        logger.error("Error processing OpenPay webhook: %s", str(e))
        # Retornamos 200 para evitar reintentos infinitos ante errores de parseo
        return {
            'statusCode': 200,
            'headers': headers_cors,
            'body': json.dumps({'error': str(e)})
        }
