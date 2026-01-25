import json
import os
import requests
from http import HTTPStatus

SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")

APPLICATION_JSON = "application/json"
headers = {
    "Content-Type": APPLICATION_JSON,
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    try:
        http_method = event.get("httpMethod")
        
        if http_method != 'POST':
            return {
                "statusCode": HTTPStatus.METHOD_NOT_ALLOWED,
                "headers": headers,
                "body": json.dumps({"message": "Method not allowed"})
            }

        body = json.loads(event.get("body", "{}"))
        timbrado_payload = body.get('timbrado')

        if not timbrado_payload:
            return {
                "statusCode": HTTPStatus.BAD_REQUEST,
                "headers": headers,
                "body": json.dumps({"message": "Payload 'timbrado' is required"})
            }

        # 1. Authenticate with SW Sapiens
        auth_response = requests.post(
            f"{SW_URL}/v2/security/authenticate",
            headers={"Content-Type": APPLICATION_JSON},
            data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
        ).json()

        if auth_response.get("status") == "error":
             return {
                "statusCode": HTTPStatus.UNAUTHORIZED,
                "headers": headers,
                "body": json.dumps({"message": "Failed to authenticate with provider", "details": auth_response.get("message")})
            }
            
        token = auth_response.get("data", {}).get("token")

        # 2. Issue Invoice (Timbrar)
        # Using v4 endpoint as seen in genera_factura_handler
        stamping_response = requests.post(
            f"{SW_URL}/v3/cfdi33/issue/json/v4",
            headers={
                "Content-Type": "application/jsontoxml",
                "Authorization": f"Bearer {token}"
            },
            data=json.dumps(timbrado_payload)
        ).json()

        status_code = HTTPStatus.OK
        if stamping_response.get("status") == "error":
            status_code = HTTPStatus.BAD_REQUEST

        return {
            "statusCode": status_code,
            "headers": headers,
            "body": json.dumps(stamping_response)
        }

    except Exception as e:
        print(f"Error in timbrado_service_handler: {str(e)}")
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "headers": headers,
            "body": json.dumps({"message": "Internal server error", "error": str(e)})
        }
