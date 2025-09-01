import json
import base64
import io
import cgi
import os
import requests

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
        if event["httpMethod"] != "POST":
            return {
                "statusCode": 405,
                "body": json.dumps({"error": "Method Not Allowed"})
            }
        
        content_type = event["headers"].get("Content-Type") or event["headers"].get("content-type")
        body = event.get("body")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body)
        else:
            body = body.encode()
        
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': str(len(body))
        }
        fp = io.BytesIO(body)
        form = cgi.FieldStorage(fp=fp, environ=environ, keep_blank_values=True)
        print("Datos del formulario:", form["key"])
        b64_key = form["key"].file.read()
        b64_cer = form["cer"].file.read()
        ctrsn = form["ctrsn"].value

        if not b64_key or not b64_cer or not ctrsn:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing parameters"}),
                "headers": headers
            }

        cert_body = {
            "type":"stamp",
            "b64key": base64.b64encode(b64_key).decode("utf-8"),
            "b64cer": base64.b64encode(b64_cer).decode("utf-8"),
            "password": ctrsn
        }
        print("Certificado preparado para envío:")
        print(cert_body)
        sw_token = requests.post(
                f"{SW_URL}/v2/security/authenticate",
                headers={"Content-Type": APPLICATION_JSON},
                data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
            ).json()

        agrega_certificado = requests.post(
            f"{SW_URL}/certificates/save",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {sw_token.get('data').get('token')}"
            },
            data=json.dumps(cert_body)
        ).json()
        print("Respuesta del servicio de certificados:", agrega_certificado)
        return {
            "statusCode": 200,
            "body": json.dumps(agrega_certificado),
            "headers": headers
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": headers
        }
