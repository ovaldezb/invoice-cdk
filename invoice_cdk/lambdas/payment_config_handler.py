import json
import os
import pymongo
from pymongo import MongoClient
import logging
from bson.json_util import dumps
from bson.objectid import ObjectId
from utils.constants import Constants
from utils.cors_utils import valida_cors

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
        # Determine User ID (sub from Cognito token)
        # This is CRITICAL for multi-tenancy. We assume authorization has passed and claims are available.
        # In API Gateway + Cognito Authorizer, claims are in requestContext.authorizer.claims
        user_id = "default_user" # Fallback
        if 'requestContext' in event and 'authorizer' in event['requestContext'] and 'claims' in event['requestContext']['authorizer']:
             user_id = event['requestContext']['authorizer']['claims']['sub']
        
        logger.info(f"Processing request for user: {user_id}")

        if event['httpMethod'] == 'GET':
            # Fetch config for this user
            config = payment_config_collection.find_one({"user_id": user_id})
            
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
            
            # Update or Insert (Upsert)
            result = payment_config_collection.update_one(
                {"user_id": user_id},
                {"$set": {"payment_config": payment_config, "user_id": user_id}},
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
