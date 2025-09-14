import json
import os
import traceback
from receptor_handler import valida_cors
from pymongo import MongoClient
from bson import json_util
from http import HTTPStatus
from dbaccess.db_certificado import (
    Certificado,
    update_certificate,
    list_certificates,
    delete_certificate,
    get_certificate_by_id,
    add_certificate
)
from dbaccess.db_sucursal import(get_sucursal_by_id, delete_sucursal)


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
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    try:
        if http_method == "POST":
            data = json.loads(body)
            certificado = Certificado(
                nombre=data["nombre"],
                rfc=data["rfc"],
                no_certificado=data["no_certificado"],
                desde=data["desde"],
                hasta=data["hasta"],
                sucursales=[],
                usuario=data["usuario"]
            )
            new_certificate = add_certificate(certificado, certificates_collection)
            return {
                "statusCode": HTTPStatus.CREATED,
                "body": json.dumps({"message": "Certificate added", "id": str(new_certificate)}),
                "headers": headers
            }
        elif http_method == "PUT": 
            cert_id = path_parameters["id"]
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
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "body": json.dumps({"message": "Internal Server Error", "error": str(e)}),
        }
