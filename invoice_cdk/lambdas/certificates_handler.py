import json
from bson import json_util
from http import HTTPStatus
from db_certificado import (
    add_certificate,
    update_certificate,
    list_certificates,
    delete_certificate,
)
from certificate import Certificado

headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    
    try:
        if http_method == "POST":
            certificate_data = json.loads(body)
            certificate = Certificado(**certificate_data)
            cert_id = add_certificate(certificate)
            return {
                "statusCode": HTTPStatus.CREATED,
                "body": json.dumps({"message": "Certificate added", "id": str(cert_id)}),
                "headers": headers
            }

        elif http_method == "PUT": 
            cert_id = path_parameters["id"]
            updated_data = json.loads(body)
            update_certificate(cert_id, updated_data)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Certificate updated"}),
                "headers": headers
            }

        elif http_method == "GET":
            print("Fetching certificates")
            certificates = list_certificates()
            for cert in certificates:
                cert["_id"] = str(cert["_id"])
                cert["desde"] = str(cert["desde"])  # Convert ObjectId to string
                cert["hasta"] = str(cert["hasta"])  # Convert ObjectId to string
            return {
                "statusCode": HTTPStatus.OK,
                "body": json_util.dumps(certificates),
                "headers": headers
            }

        elif http_method == "DELETE":
            cert_id = path_parameters["id"]
            delete_certificate(cert_id)
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
