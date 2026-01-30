import json
import os
import pymongo
from pymongo import MongoClient
import logging
from bson.json_util import dumps
from bson.objectid import ObjectId
from constantes import Constants
from utils import valida_cors

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurar MongoDB
client = MongoClient(os.environ['MONGODB_URI'])
db = client[os.environ['DB_NAME']]
payment_config_collection = db['payment_configurations']
headers = Constants.HEADERS.copy()

def handler(event, context):
    logger.info("Payment Config Event received")
    origin = event.get('headers', {}).get('origin')
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    
    if event['httpMethod'] == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    try:
        # Use a global identifier for payment configuration instead of user_id
        config_filter = {"config_id": "global"}
        
        if event['httpMethod'] == 'GET':
            # Fetch global config
            config = payment_config_collection.find_one(config_filter)
            
            # Helper to return clean array
            payment_config = config.get('payment_config', []) if config else []
            
            return {
                'statusCode': 200, 
                'headers': headers, 
                'body': dumps({'payment_config': payment_config})
            }

        elif event['httpMethod'] == 'POST':
            body = json.loads(event['body'])
            payment_config = body.get('payment_config', [])
            
            # Update or Insert (Upsert) using the global config_id
            result = payment_config_collection.update_one(
                config_filter,
                {"$set": {"payment_config": payment_config}},
                upsert=True
            )
            
            return {
                'statusCode': 200, 
                'headers': headers, 
                'body': json.dumps({'message': 'Configuration saved successfully'})
            }
            
        else:
             return {
                'statusCode': 405,
                'headers': headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }

    except Exception as e:
        logger.error("Error in Payment Config Handler: %s", str(e))
        return {
            'statusCode': 500, 
            'headers': headers, 
            'body': json.dumps({'error': str(e)})
        }
