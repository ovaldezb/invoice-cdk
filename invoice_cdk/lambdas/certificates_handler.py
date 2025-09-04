import json
import os
from pymongo import MongoClient
from bson import json_util
from http import HTTPStatus
from db_certificado import (
    update_certificate,
    list_certificates,
    delete_certificate,
    get_certificate_by_id
)
from db_sucursal import(get_sucursal_by_id, delete_sucursal)



client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
certificates_collection = db["certificates"]
sucursal_collection = db["sucursales"]

headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    print(f"Received event: {event}")
    try:
        if http_method == "PUT": 
            cert_id = path_parameters["id"]
            print(f"Updating certificate with ID: {cert_id} and data: {body}")
            updated_data = json.loads(body)
            del updated_data["_id"]
            update_certificate(cert_id, updated_data, certificates_collection)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Certificate updated"}),
                "headers": headers
            }

        elif http_method == "GET":
            usuario = path_parameters.get("id")
            print(usuario)
            certificates = list_certificates(usuario,certificates_collection)
            for cert in certificates:
                cert["_id"] = str(cert["_id"])
                cert["desde"] = str(cert["desde"])  # Convert ObjectId to string
                cert["hasta"] = str(cert["hasta"])  # Convert ObjectId to string
                sucursales = []
                for sucursal_id in cert.get("sucursales", []):
                    sucursal = get_sucursal_by_id(sucursal_id["_id"], sucursal_collection)
                    if sucursal:
                        sucursal["_id"] = str(sucursal["_id"])
                        sucursales.append(sucursal)
                cert["sucursales"] = sucursales
            return {
                "statusCode": HTTPStatus.OK,
                "body": json_util.dumps(certificates),
                "headers": headers
            }

        elif http_method == "DELETE":
            cert_id = path_parameters["id"]
            certificate = get_certificate_by_id(cert_id, certificates_collection)
            sucursales = certificate["sucursales"] 
            for sucursal in sucursales:
                delete_sucursal(sucursal["_id"], sucursal_collection)
            delete_certificate(cert_id, certificates_collection)
            
            return {
                "statusCode": HTTPStatus.OK,
                "body": json_util.dumps({"message": "Certificate deleted"}),
                "headers": headers
            }

        else:
            return {
                "statusCode": HTTPStatus.METHOD_NOT_ALLOWED,
                "body": json.dumps({"message": "Method Not Allowed"}),
                "headers": headers
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "body": json.dumps({"message": "Internal Server Error", "error": str(e)}),
        }
