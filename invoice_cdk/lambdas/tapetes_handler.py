import json
import os
import requests
from db_sucursal import get_sucursal_by_codigo
from db_certificado import get_certificate_by_id
from pymongo import MongoClient

user_name = os.getenv("USER_NAME")
password = os.getenv("PASSWORD")
tapetes_api_url = os.getenv("TAPETES_API_URL")
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
sucursal_collection = db["sucursales"]
certificado_collection = db["certificates"]


headersEndpoint = {
    'Content-Type': 'application/x-www-form-urlencoded',
}
headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    try:
        # Call external API endpoint
        if http_method == "GET":
            form_data = {
                "username": user_name,
                "password": password
            }
            response = requests.post(
                f"{tapetes_api_url}token", 
                headers=headersEndpoint, 
                data=form_data
            )
            token = response.json().get("access_token")
            ticket = path_parameters["ticket"]
            venta = requests.post(
                f"{tapetes_api_url}tickets",
                headers={"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {token}"},
                data=json.dumps({"ticket": ticket})
            )
            venta_respuesta = venta.json()
            print(f"Venta response: {venta_respuesta}")
            if 'detail' in venta_respuesta:
                print(f"Detail: {venta_respuesta['detail']}")
            if 'detail' in venta_respuesta:
                return {
                    "statusCode": 404,
                    "headers": headers,
                    "body": json.dumps({"message": venta_respuesta["detail"]})
                }
            sucursal = venta_respuesta.get("sucursal")
            print(f"Sucursal: {sucursal}")
            sucursal_data = get_sucursal_by_codigo(sucursal, sucursal_collection)
            if not sucursal_data:
                return {
                    "statusCode": 404,
                    "headers": headers,
                    "body": json.dumps({"message": "Sucursal no encontrada, consúltalo con el Administrador"})
                }
            id_certificado = sucursal_data.get("id_certificado")
            certificado = get_certificate_by_id(id_certificado, certificado_collection)
            if not certificado:
                return {
                    "statusCode": 404,
                    "headers": headers,
                    "body": json.dumps({"message": "Certificado no encontrado, consúltalo con el Administrador"})
                }
            certificado["_id"] = str(certificado["_id"])
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(
                    {
                        "venta": venta.json(),
                        "certificado": certificado
                    }
                )
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": str(e)
            })
        }