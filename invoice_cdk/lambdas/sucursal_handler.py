import json
import os
from constantes import Constants
from receptor_handler import valida_cors
from pymongo import MongoClient
from http import HTTPStatus
from dbaccess.db_sucursal import (
    add_sucursal,
    update_sucursal,
    delete_sucursal,
    get_sucursal_by_codigo,
    get_sucursal_by_id
)
from dbaccess.db_certificado import (update_certificate, get_certificate_by_id)
from models.sucursal import Sucursal
headers = Constants.HEADERS.copy()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
sucursal_collection = db["sucursales"]
certificado_collection = db["certificates"]
folio_collection = db["folios"]

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)

    try:
        if http_method == Constants.POST:
            print("Creating new sucursal with body:", body)
            sucursal_data = json.loads(body)
            sucursal = Sucursal(**sucursal_data)
            sucursal_id = add_sucursal(sucursal, sucursal_collection)        
            return {
                Constants.STATUS_CODE: HTTPStatus.CREATED,
                Constants.BODY: json.dumps({"message": "Sucursal added", "id": str(sucursal_id)}),
                Constants.HEADERS_KEY: headers
            }
        elif http_method == Constants.GET:
            if path_parameters and "id" in path_parameters:
                sucursal_id = path_parameters["id"]
                sucursal = get_sucursal_by_codigo(sucursal_id, sucursal_collection)
                if sucursal:
                    sucursal["_id"] = str(sucursal["_id"])
                    return {
                        Constants.STATUS_CODE: HTTPStatus.OK,
                        Constants.BODY: json.dumps(sucursal),
                        Constants.HEADERS_KEY: headers
                    }
                else:
                    return {
                        Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                        Constants.BODY: json.dumps({"error": "Sucursal not found"}),
                        Constants.HEADERS_KEY: headers
                    }
            else:
                sucursales = list(sucursal_collection.find())
                for suc in sucursales:
                    suc["_id"] = str(suc["_id"])
                return {
                    Constants.STATUS_CODE: HTTPStatus.OK,
                    Constants.BODY: json.dumps(sucursales),
                    Constants.HEADERS_KEY: headers
                }

        elif http_method == Constants.PUT:
            sucursal_id = path_parameters["id"]
            updated_data = json.loads(body)
            del updated_data["_id"]
            update_sucursal(sucursal_id, updated_data, sucursal_collection)
            sucursal_actualizada = get_sucursal_by_id(sucursal_id, sucursal_collection)
            sucursal_actualizada["_id"] = str(sucursal_actualizada["_id"]) if sucursal_actualizada else None
            #print(f"Sucursal updated: {sucursal_actualizada}")
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.BODY: json.dumps({"message": "Sucursal updated", "sucursal": sucursal_actualizada}),
                Constants.HEADERS_KEY: headers
            }

        elif http_method == Constants.DELETE:
            sucursal_id = path_parameters["id"]
            sucursal = get_sucursal_by_id(sucursal_id, sucursal_collection)
            certificado = sucursal["id_certificado"]
            certificado_found = get_certificate_by_id(certificado, certificado_collection)
            if certificado_found:
                #print(f"Deleting certificate with ID: {certificado_found}")
                sucursales = certificado_found.get("sucursales", [])
                new_sucursales = []
                for sucursal_loop in sucursales:
                    if sucursal_loop["_id"] != sucursal_id:
                        new_sucursales.append(sucursal_loop)
                certificado_found["sucursales"] = new_sucursales
                # Remove _id before updating to avoid "immutable field" error
                cert_id = certificado_found.pop("_id")
                update_certificate(cert_id, certificado_found, certificado_collection)

            folio_collection.delete_one({"sucursal": sucursal["codigo_sucursal"]})
            delete_sucursal(sucursal_id, sucursal_collection)
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.BODY: json.dumps({"message": "Sucursal deleted"}),
                Constants.HEADERS_KEY: headers
            }

    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.BODY: json.dumps({"error": str(e)}),
            Constants.HEADERS_KEY: headers
        }