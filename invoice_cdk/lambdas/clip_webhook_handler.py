import json
import os
import logging
from pymongo import MongoClient
from datetime import datetime
from constantes import Constants
from utils import valida_cors

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurar MongoDB
client = None
db = None
payments_collection = None

def get_db_collection():
    global client, db, payments_collection
    if client is None:
        try:
            client = MongoClient(os.environ['MONGODB_URI'])
            db = client[os.environ['DB_NAME']]
            payments_collection = db['payments']
        except Exception as e:
            logger.error("Error connecting to MongoDB: %s", str(e))
    return payments_collection

def handler(event, context):
    logger.info("Clip Webhook Event received: %s", json.dumps(event))

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
        if event['httpMethod'] != 'POST':
            return {
                'statusCode': 405,
                'headers': headers_cors,
                'body': json.dumps({'error': 'Method not allowed'})
            }

        body = json.loads(event.get('body', '{}'))
        logger.info("Webhook body parsing successful: %s", body)

        status = body.get('status', 'PENDING')
        amount_str = body.get('amount', '0')
        receipt_no = body.get('receipt_no', '')
        
        # Determine internal status
        internal_status = 'pending'
        if status in ['APPROVED', 'PAID']:
            internal_status = 'approved'
        elif status in ['DECLINED', 'CANCELLED', 'ERROR', 'FAILED']:
            internal_status = 'rejected'
        
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0

        # Build payment record
        payment_record = {
            'provider': 'CLIP',
            'status': internal_status,
            'transaction_amount': amount,
            'date_created': datetime.utcnow().isoformat() + "Z", # Formato ISO8601
            'original_payload': body,
            'receipt_no': receipt_no
        }

        collection = get_db_collection()
        if collection is not None:
            if receipt_no:
                collection.update_one(
                    {'receipt_no': receipt_no, 'provider': 'CLIP'},
                    {'$set': payment_record},
                    upsert=True
                )
                logger.info("Payment record updated/upserted into MongoDB with status: %s", internal_status)
            else:
                collection.insert_one(payment_record)
                logger.info("Payment record inserted into MongoDB with status: %s", internal_status)
        else:
            logger.error("Could not obtain DB collection reference")
            return {
                'statusCode': 500,
                'headers': headers_cors,
                'body': json.dumps({'error': 'DB Connection failed'})
            }

        return {
            'statusCode': 200,
            'headers': headers_cors,
            'body': json.dumps({'message': 'Webhook received successfully'})
        }

    except Exception as e:
        logger.error("Error processing Clip Webhook: %s", str(e))
        return {
            'statusCode': 500,
            'headers': headers_cors,
            'body': json.dumps({'error': str(e)})
        }
