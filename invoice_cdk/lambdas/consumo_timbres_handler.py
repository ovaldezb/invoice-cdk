import os
import json
from pymongo import MongoClient
from dbaccess.db_timbres import (consulta_facturas_emitidas_by_certificado)
from dbaccess.db_certificado import (list_certificates)

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
certificates_collection = db["certificates"]
facturas_emitidas_collection = db["facturasemitidas"]

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def lambda_handler(event, context):
    print("Event:", event)
    try:
        http_method = event["httpMethod"]
        path_parameters = event.get("pathParameters")
        if http_method == 'GET':
            usuario = path_parameters.get("usuario")
            if usuario:
                desde = event['queryStringParameters'].get('desde')
                hasta = event['queryStringParameters'].get('hasta')
                lista_certificados = list_certificates(usuario, certificates_collection)
                for cert in lista_certificados:
                    print(f"Procesando certificado: {cert['_id']}")
                    facturas_emitidas = consulta_facturas_emitidas_by_certificado(
                        str(cert['_id']), desde, hasta, facturas_emitidas_collection)
                    cert['facturas_emitidas'] = facturas_emitidas
                
                return {
                    'statusCode': 200,
                    'body': json.dumps(lista_certificados, default=str),
                    'headers': HEADERS
                }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': HEADERS
        }