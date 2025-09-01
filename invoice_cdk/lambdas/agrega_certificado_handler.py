import json
import base64
import os
import requests
import hashlib
from requests_toolbelt.multipart import decoder

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
        print("Event recibido:", event["body"])

        if event.get("isBase64Encoded"):
            print("Body está en Base64, decodificando.")
            body = base64.b64decode(event["body"])
        else:
            print("Body no está en Base64, procesando directamente.")
            body = event["body"].encode() 
        print("Body procesado:", body[:100])  # Imprime los primeros 100 caracteres para evitar logs muy largos
        content_type = event["headers"].get("Content-Type") or event["headers"].get("content-type")
        #print("Content-Type:", content_type)
        multipart_data = decoder.MultipartDecoder(body, content_type)
        key_bytes = None
        cer_bytes = None
        ctrsn = None
        for part in multipart_data.parts:
            content_disposition = part.headers[b"Content-Disposition"].decode()
            #print("Part Content-Disposition:", content_disposition)
            if 'name="key"' in content_disposition:
                key_bytes = part.content
            elif 'name="cer"' in content_disposition:
                cer_bytes = part.content
            elif 'name="ctrsn"' in content_disposition:
                ctrsn = part.text

        if not key_bytes or not cer_bytes or not ctrsn:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing parameters"}),
                "headers": headers
            }
        print("Tamaño key:", len(key_bytes))
        print("Tamaño cer:", len(cer_bytes))
        print("MD5 key:", hashlib.md5(key_bytes).hexdigest())
        print("MD5 cer:", hashlib.md5(cer_bytes).hexdigest())
        b64_key = base64.b64encode(key_bytes).decode("utf-8")
        b64_cer = base64.b64encode(cer_bytes).decode("utf-8")

        cert_body = {
            "type":"stamp",
            "b64Cer": b64_cer,
            "b64Key": b64_key,
            "password": ctrsn
        }
        print("Certificado preparado para envío:")
        print(cert_body)
        sw_token = requests.post(
                f"{SW_URL}/v2/security/authenticate",
                headers={"Content-Type": APPLICATION_JSON},
                data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
            ).json()
        print("Token {}".format(sw_token.get('data').get('token')))
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
