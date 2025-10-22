from http import HTTPStatus
import json
import base64
import os
import traceback
import requests
import re
from bson import json_util
from constantes import Constants
from utils import valida_cors
from models.certificate import Certificado
from requests_toolbelt.multipart import decoder
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pymongo import MongoClient
from dbaccess.db_certificado import (
    Certificado,
    update_certificate,
    delete_certificate,
    get_certificate_by_id
)
from dbaccess.db_sucursal import(delete_sucursal)

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]  
certificates_collection = db["certificates"]
sucursal_collection = db["sucursales"]
SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")

headers = Constants.HEADERS.copy()

def handler(event, context):
    event_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    try:
        if event_method == Constants.DELETE:
            cert_id = path_parameters["id"]
            certificate = get_certificate_by_id(cert_id, certificates_collection)
            sucursales = certificate["sucursales"] 
            for sucursal in sucursales:
                delete_sucursal(sucursal["_id"], sucursal_collection)
            delete_certificate(cert_id, certificates_collection)
            sw_token = requests.post(
                    f"{SW_URL}/v2/security/authenticate",
                    headers={"Content-Type": Constants.APPLICATION_JSON},
                    data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
                ).json()
            
            requests.delete(
                f"{SW_URL}/certificates/"+certificate["no_certificado"],
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {sw_token.get('data').get('token')}"
                }
            ).json()

            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.BODY: json_util.dumps({"message": "Certificate deleted"}),
                Constants.HEADERS_KEY: headers
            }
        elif event_method == Constants.POST:
            if event.get("isBase64Encoded"):
                body = base64.b64decode(event["body"])
            else:
                body = event["body"].encode() 
            
            content_type = event["headers"].get("Content-Type") or event["headers"].get("content-type")
            multipart_data = decoder.MultipartDecoder(body, content_type)
            key_bytes = None
            cer_bytes = None
            ctrsn = None
            usuario = None
            for part in multipart_data.parts:
                content_disposition = part.headers[b"Content-Disposition"].decode()
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
                    Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                    Constants.BODY: json.dumps({"error": "Faltan Parametros obligatorios"}),
                    Constants.HEADERS_KEY: headers
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

            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
        
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
                    headers={"Content-Type": Constants.APPLICATION_JSON},
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

            return {
                Constants.STATUS_CODE: HTTPStatus.CREATED,
                Constants.BODY: certificado.json(),
                Constants.HEADERS_KEY: headers
            }
        elif event_method == Constants.PUT:
            #Lee los archivos multipart
            if event.get("isBase64Encoded"):
                body = base64.b64decode(event["body"])
            else:
                body = event["body"].encode() 
            
            content_type = event["headers"].get("Content-Type") or event["headers"].get("content-type")
            multipart_data = decoder.MultipartDecoder(body, content_type)
            key_bytes = None
            cer_bytes = None
            ctrsn = None
            usuario = None
            id_cert = None
            for part in multipart_data.parts:
                content_disposition = part.headers[b"Content-Disposition"].decode()
                if 'name="key"' in content_disposition:
                    key_bytes = part.content
                elif 'name="cer"' in content_disposition:
                    cer_bytes = part.content
                elif 'name="ctrsn"' in content_disposition:
                    ctrsn = part.text
                elif 'name="usuario"' in content_disposition:
                    usuario = part.text
                elif 'name="idCertificado"' in content_disposition:
                    id_cert = part.text
            if not key_bytes or not cer_bytes or not ctrsn or not id_cert:
                return {
                    Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                    Constants.BODY: json.dumps({"message": "Faltan Parametros obligatorios"}),
                    Constants.HEADERS_KEY: headers
                }
            cert_x509 = x509.load_der_x509_certificate(cer_bytes, default_backend())
            certificado = get_certificate_by_id(id_cert, certificates_collection)
            rfc_inicial = certificado["rfc"]
            #obtiene  RFC del certificado actualizado
            subject = cert_x509.subject.rfc4514_string()
            rfc_match = re.search(r'2\.5\.4\.45=([A-Z0-9]+)', subject)
            rfc_nuevo= rfc_match.group(1) if rfc_match else None
            if rfc_inicial != rfc_nuevo:
                return {
                    Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                    Constants.BODY: json.dumps({"message": "El RFC del certificado no coincide con el inicial"}),
                    Constants.HEADERS_KEY: headers
                }
            # Extrae número de certificado
            serial_number = cert_x509.serial_number
            serial_bytes = serial_number.to_bytes((serial_number.bit_length() + 7) // 8, byteorder='big')
            # Decodifica los bytes a string (ISO-8859-1 es común en certificados)
            serial_str = serial_bytes.decode('latin1')
            # Extrae nombre
            nombre_match = re.search(r'CN=([^,]+)', subject)
            nombre = nombre_match.group(1) if nombre_match else None

            not_before = cert_x509.not_valid_before
            not_after = cert_x509.not_valid_after
            b64_key = base64.b64encode(key_bytes).decode("utf-8")
            b64_cer = base64.b64encode(cer_bytes).decode("utf-8")

            cert_body = {
                "type":"stamp",
                "b64Cer": b64_cer,
                "b64Key": b64_key,
                "password": ctrsn
            }
            #Obtengo token de Sw sapien
            sw_token = requests.post(
                    f"{SW_URL}/v2/security/authenticate",
                    headers={"Content-Type": Constants.APPLICATION_JSON},
                    data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
                ).json()
            #Elmino certificado anterior en SW Sapien
            requests.delete(
                f"{SW_URL}/certificates/"+certificado["no_certificado"],
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {sw_token.get('data').get('token')}"
                }
            ).json()
            #Guardo el nuevo certificado en SW Sapien
            requests.post(
                f"{SW_URL}/certificates/save",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {sw_token.get('data').get('token')}"
                },
                data=json.dumps(cert_body)
            ).json()

            #actualizar la base de datos con los datos del nuevo certificado
            data={
                "desde": not_before,
                "hasta": not_after,
                "no_certificado": serial_str,

            }
            
            update_certificate(id_cert, data, certificates_collection)
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.BODY: json.dumps({"message": "Certificado actualizado correctamente"}),
                Constants.HEADERS_KEY: headers
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(e)}),
            "headers": headers
        }
