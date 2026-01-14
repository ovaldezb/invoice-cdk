from http import HTTPStatus
import json
import os
import requests
from dbaccess.db_sucursal import get_sucursal_by_codigo
from dbaccess.db_certificado import get_certificate_by_id
from dbaccess.db_datos_factura import get_descripcion_by_clave
from constantes import Constants
from pymongo import MongoClient
from utils import valida_cors



user_name = os.getenv("TAPETES_USER_NAME")
password = os.getenv("TAPETES_PASSWORD")
tapetes_api_url = os.getenv("TAPETES_API_URL")
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
sucursal_collection = db["sucursales"]
certificado_collection = db["certificates"]
medidas_collection = db["medidas"]

headers = Constants.HEADERS.copy()
headersEndpoint = {
    'Content-Type': 'application/x-www-form-urlencoded',
}


def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    try:
        # Call external API endpoint
        if http_method == Constants.GET:
            form_data = {
                "username": user_name,
                "password": password
            }
            response = requests.post(
                f"{tapetes_api_url}token", 
                headers=headersEndpoint, 
                data=form_data
            )
            print('Token')
            token = response.json().get("access_token")
            ticket = path_parameters["ticket"]
            print(f'Ticket: {ticket}')
            venta = requests.post(
                f"{tapetes_api_url}tickets",
                headers={"Accept": Constants.APPLICATION_JSON, "Content-Type": Constants.APPLICATION_JSON, "Authorization": f"Bearer {token}"},
                data=json.dumps({"ticket": ticket})
            )
            venta_respuesta = venta.json()
            print(f'Venta: {venta_respuesta}')
            if 'detail' in venta_respuesta:
                return {
                    Constants.STATUS_CODE: 404,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({"message": venta_respuesta["detail"]})
                }
            sucursal = venta_respuesta.get("sucursal")
            sucursal_data = get_sucursal_by_codigo(sucursal, sucursal_collection)
            if not sucursal_data:
                return {
                    Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({"message": "Sucursal no encontrada, consúltalo con el Administrador"})
                }
            detalle = venta_respuesta.get("detalle")
            for item in detalle:
                clave = item.get("claveunidad")
                descripcion = get_descripcion_by_clave(clave, medidas_collection)
                item['unidad'] = descripcion
            id_certificado = sucursal_data.get("id_certificado")
            certificado = get_certificate_by_id(id_certificado, certificado_collection)
            print(f'Certificado: {certificado}')
            if not certificado:
                return {
                    Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({"message": "Certificado no encontrado, consúltalo con el Administrador"})
                }
            
            sucursal_data["_id"] = str(sucursal_data["_id"])
            return {
                Constants.STATUS_CODE: 200,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps(
                    {
                        "venta": venta_respuesta,
                        "certificado": certificado,
                        "sucursal": sucursal_data
                    }
                )
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.HEADERS_KEY: headers,
            Constants.BODY: json.dumps({
                "error": str(e)
            })
        }