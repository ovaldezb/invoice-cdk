import json
import os
import pymongo
from pymongo import MongoClient
import logging
from bson.json_util import dumps

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurar MongoDB
client = MongoClient(os.environ['MONGODB_URI'])
db = client[os.environ['DB_NAME']]
payments_collection = db['payments']
headers = Constants.HEADERS.copy()

def handler(event, context):
    logger.info("Get Payments Event received",event)
    origin = event.get('headers', {}).get('origin')
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)

    if event['httpMethod'] == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    if event['httpMethod'] != 'GET':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'error': 'Method not allowed'})
        }

    try:
        # Consultar últimos 3 pagos, ordenados por fecha de creación descendente
        # Filtramos por algo si fuera necesario (ej. usuario), pero por ahora traemos los últimos globales 
        # o asumimos que se filtrará por token si implementamos esa lógica (aquí es global de la colección).
        # TODO: Filtrar por usuario logueado usando el 'external_reference' o similar si estuviera disponible en el contexto.
        
        cursor = payments_collection.find().sort("date_created", pymongo.DESCENDING).limit(3)
        payments = list(cursor)

        logger.info(f"Retrieved {len(payments)} payments")

        return {
            'statusCode': 200, 
            'headers': headers, 
            'body': dumps(payments) # dumps de bson maneja ObjectIds y fechas
        }

    except Exception as e:
        logger.error("Error fetching payments: %s", str(e))
        return {
            'statusCode': 500, 
            'headers': headers, 
            'body': json.dumps({'error': str(e)})
        }
