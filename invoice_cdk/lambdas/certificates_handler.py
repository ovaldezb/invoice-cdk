import json
from http import HTTPStatus
from db_service import (
    add_certificate,
    update_certificate,
    list_certificates,
    delete_certificate,
)
from certificate import Certificado
import os

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    print(body)
    print(http_method)
    print(os.getenv("MONGODB_URI"))
    try:
        if http_method == "POST":
            certificate_data = json.loads(body)
            certificate = Certificado(**certificate_data)
            cert_id = add_certificate(certificate)
            return {
                "statusCode": HTTPStatus.CREATED,
                "body": json.dumps({"message": "Certificate added", "id": str(cert_id)}),
            }

        elif http_method == "PUT":
            cert_id = path_parameters["id"]
            updated_data = json.loads(body)
            update_certificate(cert_id, updated_data)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Certificate updated"}),
            }

        elif http_method == "GET":
            certificates = list_certificates()
            for cert in certificates:
                cert["_id"] = str(cert["_id"])  # Convert ObjectId to string
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps(certificates),
            }

        elif http_method == "DELETE":
            cert_id = path_parameters["id"]
            delete_certificate(cert_id)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Certificate deleted"}),
            }

        else:
            return {
                "statusCode": HTTPStatus.METHOD_NOT_ALLOWED,
                "body": json.dumps({"message": "Method Not Allowed"}),
            }

    except Exception as e:
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "body": json.dumps({"message": "Internal Server Error", "error": str(e)}),
        }
