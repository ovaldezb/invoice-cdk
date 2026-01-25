import json
import os
import pymongo
from pymongo import MongoClient
import logging
from datetime import datetime, timedelta, timezone
from bson.json_util import dumps
from constantes import Constants
from utils import valida_cors

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurar MongoDB
client = MongoClient(os.environ['MONGODB_URI'])
db = client[os.environ['DB_NAME']]
facturas_collection = db['facturasemitidas']
headers = Constants.HEADERS.copy()

def handler(event, context):
    logger.info("Get Invoice Count Event received: %s", json.dumps(event))
    origin = event.get('headers', {}).get('origin')
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    
    if event['httpMethod'] == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    # Validar fechas
    try:
        query_params = event.get('queryStringParameters') or {}
        month_param = query_params.get('month')
        year_param = query_params.get('year')

        if month_param and year_param:
            month = int(month_param)
            year = int(year_param)
        else:
            today = datetime.now()
            first_day_this_month = today.replace(day=1)
            last_month_date = first_day_this_month - timedelta(days=1)
            month = last_month_date.month
            year = last_month_date.year

        # Calcular rango (objetos datetime con UTC para consistencia)
        start_date = datetime(year, month, 1).replace(tzinfo=timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1).replace(tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1).replace(tzinfo=timezone.utc)
            
        logger.info(f"Counting invoices between {start_date} and {end_date}")

        # Contar Facturas Emitidas directamente por fecha
        query = {
            "fechaTimbrado": {
                "$gte": start_date,
                "$lt": end_date
            }
        }
        
        count = facturas_collection.count_documents(query)

        response_body = {
            "count": count,
            "period": f"{month}/{year}"
        }

        return {
            'statusCode': 200, 
            'headers': headers, 
            'body': json.dumps(response_body)
        }

    except Exception as e:
        logger.error("Error counting invoices: %s", str(e))
        return {
            'statusCode': 500, 
            'headers': headers, 
            'body': json.dumps({'error': str(e)})
        }
