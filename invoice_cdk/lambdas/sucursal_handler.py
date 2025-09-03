import json
import os
from pymongo import MongoClient
from http import HTTPStatus
from db_sucursal import (
    add_sucursal,
    update_sucursal,
    delete_sucursal,
    get_sucursal_by_codigo,
    get_sucursal_by_id
)
from db_certificado import (update_certificate, get_certificate_by_id)
from sucursal import Sucursal
headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
sucursal_collection = db["sucursales"]
certificado_collection = db["certificates"]

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    print(f"Received event: {event}")
    try:
        if http_method == "POST":
            print(f"Creating new sucursal with data: {body}")
            sucursal_data = json.loads(body)
            sucursal = Sucursal(**sucursal_data)
            sucursal_id = add_sucursal(sucursal, sucursal_collection)
            print(f"Sucursal created with ID: {sucursal_id}")
            return {
                "statusCode": HTTPStatus.CREATED,
                "body": json.dumps({"message": "Sucursal added", "id": str(sucursal_id)}),
                "headers": headers
            }
        elif http_method == "GET":
            if path_parameters and "id" in path_parameters:
                sucursal_id = path_parameters["id"]
                sucursal = get_sucursal_by_codigo(sucursal_id, sucursal_collection)
                if sucursal:
                    sucursal["_id"] = str(sucursal["_id"])
                    return {
                        "statusCode": HTTPStatus.OK,
                        "body": json.dumps(sucursal),
                        "headers": headers
                    }
                else:
                    return {
                        "statusCode": HTTPStatus.NOT_FOUND,
                        "body": json.dumps({"error": "Sucursal not found"}),
                        "headers": headers
                    }
            else:
                sucursales = list(sucursal_collection.find())
                for suc in sucursales:
                    suc["_id"] = str(suc["_id"])
                return {
                    "statusCode": HTTPStatus.OK,
                    "body": json.dumps(sucursales),
                    "headers": headers
                }

        elif http_method == "PUT":
            sucursal_id = path_parameters["id"]
            updated_data = json.loads(body)
            del updated_data["_id"]
            update_sucursal(sucursal_id, updated_data, sucursal_collection)
            sucursal_actualizada = get_sucursal_by_id(sucursal_id, sucursal_collection)
            sucursal_actualizada["_id"] = str(sucursal_actualizada["_id"]) if sucursal_actualizada else None
            #print(f"Sucursal updated: {sucursal_actualizada}")
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Sucursal updated", "sucursal": sucursal_actualizada}),
                "headers": headers
            }

        elif http_method == "DELETE":
            sucursal_id = path_parameters["id"]
            sucursal = get_sucursal_by_id(sucursal_id, sucursal_collection)
            certificado = sucursal["id_certificado"]
            certificado_found = get_certificate_by_id(certificado, certificado_collection)
            if certificado_found:
                #print(f"Deleting certificate with ID: {certificado_found}")
                sucursales = certificado_found.get("sucursales", [])
                new_sucursales = []
                for sucursal in sucursales:
                    if sucursal["_id"] != sucursal_id:
                        new_sucursales.append(sucursal)
                certificado_found["sucursales"] = new_sucursales
                update_certificate(certificado_found["_id"], certificado_found, certificado_collection)
            delete_sucursal(sucursal_id, sucursal_collection)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Sucursal deleted"}),
                "headers": headers
            }

    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "body": json.dumps({"error": str(e)}),
            "headers": headers
        }