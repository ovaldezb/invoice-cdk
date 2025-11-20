import os
import json
import traceback
from http import HTTPStatus
from utils import valida_cors
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from constantes import Constants
from dbaccess.db_bitacora import buscar_bitacora_por_fechas

# Configuración de MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
bitacora_collection = db["bitacora"]

# Headers de respuesta
headers = Constants.HEADERS.copy()

def handler(event, context):
    """
    Handler para consultar la bitácora de actividades.
    
    GET /consulta-bitacora?fechaInicio=YYYY-MM-DDTHH:MM:SS&fechaFin=YYYY-MM-DDTHH:MM:SS
    """
    print(event)
    try:
        http_method = event["httpMethod"]
        origin = event.get("headers", {}).get("origin")
        headers["Access-Control-Allow-Origin"] = valida_cors(origin)
        if http_method == Constants.GET:
            # Obtener parámetros de query string
            query_params = event.get("queryStringParameters", {})
            
            if not query_params:
                return {
                    Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({
                        "message": "Faltan parámetros requeridos: fechaInicio y fechaFin"
                    })
                }
            
            fecha_inicio = query_params.get("fechaInicio")+"T00:00:00"
            fecha_fin = query_params.get("fechaFin")+"T23:59:59"
            
            # Validar que los parámetros estén presentes
            if not fecha_inicio or not fecha_fin:
                return {
                    Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({
                        "message": "Los parámetros fechaInicio y fechaFin son requeridos"
                    })
                }
            
            # Validar formato de fechas
            try:
                datetime.fromisoformat(fecha_inicio.replace('Z', '+00:00'))
                datetime.fromisoformat(fecha_fin.replace('Z', '+00:00'))
            except ValueError:
                return {
                    Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({
                        "message": "Formato de fecha inválido. Use formato ISO: YYYY-MM-DDTHH:MM:SS"
                    })
                }
            
            # Buscar registros en la bitácora
            registros, total_registros = buscar_bitacora_por_fechas(fecha_inicio, fecha_fin, bitacora_collection)
            if total_registros == 0:
                return {
                    Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({
                        "message": "No se encontraron registros en la bitácora para el rango de fechas proporcionado"
                    })
                }
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({
                    "data": registros,
                    "total": total_registros,
                })
            }
        
        else:
            return {
                Constants.STATUS_CODE: HTTPStatus.METHOD_NOT_ALLOWED,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({
                    "message": f"Método {http_method} no permitido"
                })
            }
    
    except Exception as e:
        print(f"Error en consulta de bitácora: {str(e)}")
        traceback.print_exc()
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.HEADERS_KEY: headers,
            Constants.BODY: json.dumps({
                "message": f"Error interno del servidor: {str(e)}"
            })
        }
