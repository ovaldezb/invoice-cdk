import json
import base64
import os
import requests
import re
from certificate import Certificado
from requests_toolbelt.multipart import decoder
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pymongo import MongoClient
from db_certificado import add_certificate  


SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
certificates_collection = db["certificates"]

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
        if event.get("isBase64Encoded"):
            body = base64.b64decode(event["body"])
        else:
            body = event["body"].encode() 
        
        content_type = event["headers"].get("Content-Type") or event["headers"].get("content-type")
        #print("Content-Type:", content_type)
        multipart_data = decoder.MultipartDecoder(body, content_type)
        key_bytes = None
        cer_bytes = None
        ctrsn = None
        usuario = None
        for part in multipart_data.parts:
            content_disposition = part.headers[b"Content-Disposition"].decode()
            #print("Part Content-Disposition:", content_disposition)
            if 'name="key"' in content_disposition:
                key_bytes = part.content
            elif 'name="cer"' in content_disposition:
                cer_bytes = part.content
            elif 'name="ctrsn"' in content_disposition:
                ctrsn = part.text
            elif 'name="usuario"' in content_disposition:
                usuario = part.text

        if not key_bytes or not cer_bytes or not ctrsn:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing parameters"}),
                "headers": headers
            }
        
        cert = x509.load_der_x509_certificate(cer_bytes, default_backend())
        serial_number = cert.serial_number
        serial_bytes = serial_number.to_bytes((serial_number.bit_length() + 7) // 8, byteorder='big')
        # Decodifica los bytes a string (ISO-8859-1 es común en certificados)
        serial_str = serial_bytes.decode('latin1')

        subject = cert.subject.rfc4514_string()
        rfc_match = re.search(r'2\.5\.4\.45=([A-Z0-9]+)', subject)
        rfc = rfc_match.group(1) if rfc_match else None

        # Extrae nombre
        nombre_match = re.search(r'CN=([^,]+)', subject)
        nombre = nombre_match.group(1) if nombre_match else None

        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
        
        b64_key = base64.b64encode(key_bytes).decode("utf-8")
        b64_cer = base64.b64encode(cer_bytes).decode("utf-8")

        cert_body = {
            "type":"stamp",
            "b64Cer": b64_cer,
            "b64Key": b64_key,
            "password": ctrsn
        }
        
        sw_token = requests.post(
                f"{SW_URL}/v2/security/authenticate",
                headers={"Content-Type": APPLICATION_JSON},
                data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
            ).json()
        
        
        requests.post(
            f"{SW_URL}/certificates/save",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {sw_token.get('data').get('token')}"
            },
            data=json.dumps(cert_body)
        ).json()

        certificado = Certificado(
            nombre=nombre,
            rfc=rfc,
            no_certificado=serial_str,
            desde=not_before,
            hasta=not_after,
            sucursales=[],
            usuario=usuario
        )
        add_certificate(certificado, certificates_collection)

        return {
            "statusCode": 200,
            "body": certificado.json(),
            "headers": headers
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": headers
        }
