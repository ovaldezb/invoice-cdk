"""
Timbrado de un CFDI 4.0 ya sellado, recibido como XML.

Endpoint: POST /timbrado-xml   (público por ahora; sin API Key)
Body:     el XML del comprobante, tal cual (Content-Type: application/xml)

A diferencia de POST /factura (SW sella con el CSD guardado), aquí el XML ya
viene sellado por el emisor, así que se usa el servicio de timbrado de SW:
POST {SW_URL}/cfdi33/stamp/v4 (multipart, campo "xml").

Flujo:
1. Valida que el body sea un XML de CFDI 4.0 con Sello, NoCertificado y Certificado.
2. Verifica que el RFC emisor tenga un certificado registrado en la plataforma.
3. Envía el XML a SW y regresa el resultado del timbrado (mismos campos que /factura).
4. Registra cada llamada en la bitácora.

No guarda la factura, no genera PDF ni envía correo: solo timbra.
"""
import os
import json
import base64
import traceback
import xml.etree.ElementTree as ET
from http import HTTPStatus
from datetime import datetime, timezone, timedelta

import requests
from pymongo import MongoClient

from constantes import Constants

SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")
SW_TIMEOUT_SECONDS = 25

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
certificates_collection = db["certificates"]
bitacora_collection = db["bitacora"]

headers = {"Content-Type": "application/json"}

NS_CFDI4 = "http://www.sat.gob.mx/cfd/4"
ATRIBUTOS_SELLO = ("Sello", "NoCertificado", "Certificado")


class TimbradoError(Exception):
    """Error que se regresa al cliente con un código HTTP específico."""

    def __init__(self, status_code, mensaje, detalle=None):
        super().__init__(mensaje)
        self.status_code = status_code
        self.mensaje = mensaje
        self.detalle = detalle


def respuesta(status_code, body):
    return {
        Constants.STATUS_CODE: status_code,
        Constants.HEADERS_KEY: headers,
        Constants.BODY: json.dumps(body, ensure_ascii=False, default=str),
    }


def obtiene_xml(event):
    """Regresa el XML del body como bytes (API Gateway puede mandarlo en base64)."""
    body = event.get("body")
    if not body:
        raise TimbradoError(HTTPStatus.BAD_REQUEST, "El cuerpo de la petición debe contener el XML del CFDI")
    if event.get("isBase64Encoded"):
        try:
            return base64.b64decode(body)
        except ValueError:
            raise TimbradoError(HTTPStatus.BAD_REQUEST, "El cuerpo de la petición no es base64 válido")
    return body.encode("utf-8")


def analiza_cfdi(xml_bytes):
    """Valida el CFDI y regresa los datos que se usan para validar y registrar."""
    try:
        raiz = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise TimbradoError(HTTPStatus.BAD_REQUEST, "El XML no es válido", str(e))

    if raiz.tag != f"{{{NS_CFDI4}}}Comprobante" or raiz.get("Version") != "4.0":
        raise TimbradoError(HTTPStatus.BAD_REQUEST, "El XML debe ser un comprobante CFDI 4.0 (cfdi:Comprobante Version=\"4.0\")")

    faltantes = [a for a in ATRIBUTOS_SELLO if not (raiz.get(a) or "").strip()]
    if faltantes:
        raise TimbradoError(
            HTTPStatus.BAD_REQUEST,
            "El XML debe venir sellado por el emisor",
            f"Atributos vacíos o faltantes: {', '.join(faltantes)}",
        )

    emisor = raiz.find(f"{{{NS_CFDI4}}}Emisor")
    receptor = raiz.find(f"{{{NS_CFDI4}}}Receptor")
    rfc_emisor = ((emisor.get("Rfc") if emisor is not None else "") or "").strip().upper()
    if not rfc_emisor:
        raise TimbradoError(HTTPStatus.BAD_REQUEST, "El XML no tiene RFC del emisor")

    return {
        "rfcEmisor": rfc_emisor,
        "rfcReceptor": ((receptor.get("Rfc") if receptor is not None else "") or "").strip().upper() or None,
        "serie": raiz.get("Serie") or "",
        "folio": raiz.get("Folio") or "",
    }


def valida_emisor(rfc_emisor):
    if not certificates_collection.find_one({"rfc": rfc_emisor}):
        raise TimbradoError(
            HTTPStatus.NOT_FOUND,
            "El RFC emisor no está registrado en la plataforma; no es posible timbrar",
        )


def obtiene_token_sw():
    resp = requests.post(
        f"{SW_URL}/v2/security/authenticate",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD}),
        timeout=SW_TIMEOUT_SECONDS,
    )
    token = ((resp.json() or {}).get("data") or {}).get("token")
    if not token:
        raise TimbradoError(HTTPStatus.BAD_GATEWAY, "No se pudo autenticar con el proveedor de timbrado")
    return token


def timbra_sw(xml_bytes):
    """Envía el XML sellado a SW. Regresa el 'data' del timbrado o lanza TimbradoError."""
    token = obtiene_token_sw()
    resp = requests.post(
        f"{SW_URL}/cfdi33/stamp/v4",
        headers={"Authorization": f"Bearer {token}"},
        files={"xml": ("cfdi.xml", xml_bytes, "application/xml")},
        timeout=SW_TIMEOUT_SECONDS,
    )
    try:
        cuerpo = resp.json() or {}
    except ValueError:
        raise TimbradoError(HTTPStatus.BAD_GATEWAY, "Respuesta inválida del proveedor de timbrado", resp.text[:500])

    if cuerpo.get("status") != "success" or not cuerpo.get("data"):
        # Rechazo del SAT/SW por el contenido del comprobante: se regresa como 400,
        # igual que en POST /factura, con el mensaje para que el cliente lo corrija.
        raise TimbradoError(
            HTTPStatus.BAD_REQUEST,
            cuerpo.get("message") or "El proveedor de timbrado rechazó el comprobante",
            cuerpo.get("messageDetail"),
        )
    return cuerpo["data"]


def registra_bitacora(datos, mensaje, status):
    """Escribe en bitácora sin poder tumbar el flujo principal."""
    try:
        datos = datos or {}
        bitacora_collection.insert_one({
            "ticket": None,
            "rfc": datos.get("rfcReceptor"),
            "rfcEmisor": datos.get("rfcEmisor"),
            "email": None,
            "mensaje": f"Timbrado XML Serie:{datos.get('serie', '')} Folio:{datos.get('folio', '')}: {mensaje}",
            "status": status,
            "traceback": "",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
        })
    except Exception:
        print("No se pudo escribir en bitacora")
        traceback.print_exc()


def handler(event, context):
    datos = None
    try:
        if event.get("httpMethod") != Constants.POST:
            return respuesta(HTTPStatus.METHOD_NOT_ALLOWED, {"message": "Método no permitido"})

        xml_bytes = obtiene_xml(event)
        datos = analiza_cfdi(xml_bytes)
        valida_emisor(datos["rfcEmisor"])

        resultado = timbra_sw(xml_bytes)
        print(f"Timbrado XML {datos['rfcEmisor']} {datos['serie']}{datos['folio']}: UUID {resultado.get('uuid')}")
        registra_bitacora(datos, f"Timbrado exitoso UUID {resultado.get('uuid')}", "exito")
        return respuesta(HTTPStatus.OK, {"status": "success", **resultado})

    except TimbradoError as e:
        registra_bitacora(datos, f"Rechazado: {e.mensaje}" + (f" | {e.detalle}" if e.detalle else ""), "error")
        cuerpo = {"status": "error", "message": e.mensaje}
        if e.detalle:
            cuerpo["detalle"] = e.detalle
        return respuesta(e.status_code, cuerpo)
    except requests.RequestException as e:
        traceback.print_exc()
        registra_bitacora(datos, f"Error de comunicación con SW: {e}", "error")
        return respuesta(HTTPStatus.BAD_GATEWAY, {"status": "error", "message": "No se pudo comunicar con el proveedor de timbrado"})
    except Exception as e:
        traceback.print_exc()
        registra_bitacora(datos, f"Error inesperado: {e}", "error")
        return respuesta(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error", "message": "Error interno al timbrar el comprobante"})
