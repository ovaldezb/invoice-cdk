"""
Cancelación de CFDI vía SW Sapien (cancelación por UUID, versión 2).

Endpoint: POST /cancelacion   (protegido con API Key de API Gateway: header x-api-key)

Lo consume un servidor (no un navegador), por eso no usa Cognito.

Body:
{
    "uuid": "UUID de la factura a cancelar",                 (obligatorio)
    "rfcEmisor": "RFC del emisor",                           (obligatorio si la factura NO la timbró este sistema)
    "rfcReceptor": "RFC del receptor",                       (obligatorio)
    "ticket": "Ticket de la venta",                          (obligatorio si la factura la timbró este sistema)
    "motivo": "01 | 02 | 03 | 04",                           (obligatorio)
    "folioSustitucion": "UUID de la factura que sustituye"   (obligatorio solo con motivo 01)
}

Flujo:
1. Valida el body (motivo del catálogo SAT, formato de UUID/RFC, folioSustitucion con motivo 01).
2. Busca el UUID en facturasemitidas:
   - Si existe (timbrada por este sistema): valida ticket y RFC receptor contra el XML,
     rechaza si ya está cancelada; el RFC emisor sale del XML.
   - Si no existe (timbrada por otro sistema): el RFC emisor debe pertenecer a un
     certificado registrado en este sistema (si su CSD no está en SW no se puede cancelar).
3. Envía la solicitud a SW: POST {SW_URL}/cfdi33/cancel/{rfc}/{uuid}/{motivo}[/{folioSustitucion}]/v2
4. Interpreta el código SAT (201 solicitud aceptada, 202 previamente cancelada) y,
   si la factura es de este sistema, actualiza su estatus y guarda el acuse.
5. Registra el resultado (éxito o rechazo) en la bitácora.
"""
import os
import re
import json
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
facturas_emitidas_collection = db["facturasemitidas"]
certificates_collection = db["certificates"]
bitacora_collection = db["bitacora"]

headers = {"Content-Type": "application/json"}

# Catálogo SAT de motivos de cancelación (vigente desde 2022)
MOTIVOS_CANCELACION = {
    "01": "Comprobante emitido con errores con relación",
    "02": "Comprobante emitido con errores sin relación",
    "03": "No se llevó a cabo la operación",
    "04": "Operación nominativa relacionada en una factura global",
}
MOTIVO_CON_RELACION = "01"

ESTATUS_VIGENTE = "Vigente"
ESTATUS_EN_PROCESO = "En proceso de cancelación"
ESTATUS_CANCELADA = "Cancelada"

# Códigos SAT que SW regresa por UUID
CODIGO_SOLICITUD_EXITOSA = "201"
CODIGO_PREVIAMENTE_CANCELADO = "202"

UUID_REGEX = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")
# RFC persona moral (12) o física (13); admite Ñ y &
RFC_REGEX = re.compile(r"^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$")


class CancelacionError(Exception):
    """Error de negocio que se regresa al cliente con un código HTTP específico."""

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


def normaliza_rfc(rfc):
    return (rfc or "").strip().upper()


def valida_solicitud(body):
    """Valida y normaliza el body. Regresa un dict con los campos limpios."""
    if not isinstance(body, dict):
        raise CancelacionError(HTTPStatus.BAD_REQUEST, "El cuerpo de la petición debe ser un objeto JSON")

    uuid = (body.get("uuid") or "").strip().upper()
    motivo = (body.get("motivo") or "").strip()
    rfc_receptor = normaliza_rfc(body.get("rfcReceptor"))
    rfc_emisor = normaliza_rfc(body.get("rfcEmisor"))
    ticket = (body.get("ticket") or "").strip()
    folio_sustitucion = (body.get("folioSustitucion") or "").strip().upper()

    errores = []
    if not UUID_REGEX.match(uuid):
        errores.append("uuid es obligatorio y debe tener formato de UUID")
    if motivo not in MOTIVOS_CANCELACION:
        errores.append(f"motivo es obligatorio y debe ser uno de: {', '.join(MOTIVOS_CANCELACION)}")
    if not RFC_REGEX.match(rfc_receptor):
        errores.append("rfcReceptor es obligatorio y debe ser un RFC válido")
    if rfc_emisor and not RFC_REGEX.match(rfc_emisor):
        errores.append("rfcEmisor no es un RFC válido")

    if motivo == MOTIVO_CON_RELACION:
        if not UUID_REGEX.match(folio_sustitucion):
            errores.append("folioSustitucion es obligatorio con motivo 01 y debe tener formato de UUID")
        elif folio_sustitucion == uuid:
            errores.append("folioSustitucion debe ser distinto del uuid a cancelar")
    elif folio_sustitucion:
        errores.append("folioSustitucion solo aplica con motivo 01")

    if errores:
        raise CancelacionError(HTTPStatus.BAD_REQUEST, "Solicitud inválida", errores)

    return {
        "uuid": uuid,
        "motivo": motivo,
        "rfcReceptor": rfc_receptor,
        "rfcEmisor": rfc_emisor,
        "ticket": ticket,
        "folioSustitucion": folio_sustitucion,
    }


def busca_factura(uuid):
    """Busca la factura sin importar si el UUID se guardó en mayúsculas o minúsculas."""
    return facturas_emitidas_collection.find_one({"uuid": {"$in": [uuid, uuid.lower()]}})


def extrae_rfcs_cfdi(cfdi_xml):
    """Regresa (rfc_emisor, rfc_receptor) leídos del XML del CFDI."""
    raiz = ET.fromstring(cfdi_xml.encode("utf-8") if isinstance(cfdi_xml, str) else cfdi_xml)
    rfc_emisor = rfc_receptor = None
    for nodo in raiz:
        nombre = nodo.tag.split("}")[-1]
        if nombre == "Emisor":
            rfc_emisor = normaliza_rfc(nodo.get("Rfc"))
        elif nombre == "Receptor":
            rfc_receptor = normaliza_rfc(nodo.get("Rfc"))
    return rfc_emisor, rfc_receptor


def resuelve_rfc_emisor(solicitud, factura):
    """Aplica las validaciones según el origen de la factura y regresa el RFC emisor."""
    if factura:
        # Factura timbrada por este sistema
        estatus = factura.get("estatus")
        if estatus == ESTATUS_CANCELADA:
            raise CancelacionError(HTTPStatus.CONFLICT, "La factura ya está cancelada")
        if estatus == ESTATUS_EN_PROCESO:
            raise CancelacionError(
                HTTPStatus.CONFLICT,
                "La factura ya tiene una solicitud de cancelación en proceso",
            )

        if not solicitud["ticket"]:
            raise CancelacionError(HTTPStatus.BAD_REQUEST, "ticket es obligatorio para facturas emitidas por este sistema")
        if solicitud["ticket"] != str(factura.get("ticket") or ""):
            raise CancelacionError(HTTPStatus.UNPROCESSABLE_ENTITY, "El ticket no corresponde a la factura")

        try:
            rfc_emisor_xml, rfc_receptor_xml = extrae_rfcs_cfdi(factura.get("cfdi") or "")
        except ET.ParseError:
            raise CancelacionError(HTTPStatus.INTERNAL_SERVER_ERROR, "No se pudo leer el XML de la factura almacenada")

        if solicitud["rfcReceptor"] != rfc_receptor_xml:
            raise CancelacionError(HTTPStatus.UNPROCESSABLE_ENTITY, "El RFC del receptor no corresponde a la factura")
        if solicitud["rfcEmisor"] and solicitud["rfcEmisor"] != rfc_emisor_xml:
            raise CancelacionError(HTTPStatus.UNPROCESSABLE_ENTITY, "El RFC del emisor no corresponde a la factura")
        if not rfc_emisor_xml:
            raise CancelacionError(HTTPStatus.INTERNAL_SERVER_ERROR, "La factura almacenada no tiene RFC emisor")
        return rfc_emisor_xml

    # Factura timbrada por otro sistema: el emisor debe tener su certificado registrado aquí
    if not solicitud["rfcEmisor"]:
        raise CancelacionError(
            HTTPStatus.BAD_REQUEST,
            "rfcEmisor es obligatorio cuando la factura no fue emitida por este sistema",
        )
    if not certificates_collection.find_one({"rfc": solicitud["rfcEmisor"]}):
        raise CancelacionError(
            HTTPStatus.NOT_FOUND,
            "El RFC emisor no tiene un certificado (CSD) registrado; no es posible cancelar",
        )
    return solicitud["rfcEmisor"]


def obtiene_token_sw():
    resp = requests.post(
        f"{SW_URL}/v2/security/authenticate",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD}),
        timeout=SW_TIMEOUT_SECONDS,
    )
    token = ((resp.json() or {}).get("data") or {}).get("token")
    if not token:
        raise CancelacionError(HTTPStatus.BAD_GATEWAY, "No se pudo autenticar con el proveedor de timbrado")
    return token


def url_cancelacion_sw(rfc_emisor, solicitud):
    url = f"{SW_URL}/cfdi33/cancel/{rfc_emisor}/{solicitud['uuid']}/{solicitud['motivo']}"
    if solicitud["folioSustitucion"]:
        # PENDIENTE DE VALIDAR en el ambiente de pruebas de SW: la colección de SW
        # solo documenta folioSustitucion como último segmento en la variante con
        # estatus; aquí se agrega antes de /v2.
        url += f"/{solicitud['folioSustitucion']}"
    return url + "/v2"


def envia_cancelacion_sw(rfc_emisor, solicitud):
    """Llama a SW y regresa (resultado_uuid, acuse) o lanza CancelacionError."""
    token = obtiene_token_sw()
    resp = requests.post(
        url_cancelacion_sw(rfc_emisor, solicitud),
        headers={"Authorization": f"Bearer {token}"},
        timeout=SW_TIMEOUT_SECONDS,
    )
    try:
        cuerpo = resp.json() or {}
    except ValueError:
        raise CancelacionError(HTTPStatus.BAD_GATEWAY, "Respuesta inválida del proveedor de timbrado", resp.text[:500])

    print(f"Respuesta SW cancelación {solicitud['uuid']}: HTTP {resp.status_code} {cuerpo.get('status')}")

    if cuerpo.get("status") != "success":
        raise CancelacionError(
            HTTPStatus.BAD_GATEWAY,
            cuerpo.get("message") or "El proveedor de timbrado rechazó la cancelación",
            cuerpo.get("messageDetail"),
        )

    data = cuerpo.get("data") or {}
    por_uuid = data.get("uuid") or {}
    # SW regresa el UUID como llave (normalmente en mayúsculas)
    resultado = por_uuid.get(solicitud["uuid"]) or por_uuid.get(solicitud["uuid"].lower())
    if resultado is None and len(por_uuid) == 1:
        resultado = next(iter(por_uuid.values()))
    if isinstance(resultado, str):  # formato V1 por si acaso
        resultado = {"code": resultado, "message": None, "description": None}
    if not isinstance(resultado, dict) or not resultado.get("code"):
        raise CancelacionError(HTTPStatus.BAD_GATEWAY, "El proveedor de timbrado no regresó el resultado del UUID")

    return resultado, data.get("acuse")


def actualiza_factura(uuid_bd, estatus, solicitud, resultado, acuse):
    facturas_emitidas_collection.update_one(
        {"uuid": uuid_bd},
        {"$set": {
            "estatus": estatus,
            "cancelacion": {
                "motivo": solicitud["motivo"],
                "folioSustitucion": solicitud["folioSustitucion"] or None,
                "codigoSat": resultado.get("code"),
                "mensajeSat": resultado.get("message"),
                "acuse": acuse,
                "fechaSolicitud": datetime.now(timezone.utc),
            },
        }},
    )


def registra_bitacora(solicitud, rfc_emisor, mensaje, status):
    """Escribe en bitácora sin poder tumbar el flujo principal."""
    try:
        solicitud = solicitud or {}
        bitacora_collection.insert_one({
            "ticket": solicitud.get("ticket") or None,
            "rfc": solicitud.get("rfcReceptor") or None,
            "rfcEmisor": rfc_emisor or solicitud.get("rfcEmisor") or None,
            "email": None,
            "mensaje": f"Cancelación UUID {solicitud.get('uuid')}: {mensaje}",
            "status": status,
            "traceback": "",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
        })
    except Exception:
        print("No se pudo escribir en bitacora")
        traceback.print_exc()


def handler(event, context):
    solicitud = None
    rfc_emisor = None
    try:
        if event.get("httpMethod") != Constants.POST:
            return respuesta(HTTPStatus.METHOD_NOT_ALLOWED, {"message": "Método no permitido"})

        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            raise CancelacionError(HTTPStatus.BAD_REQUEST, "El cuerpo de la petición no es JSON válido")

        solicitud = valida_solicitud(body)
        factura = busca_factura(solicitud["uuid"])
        rfc_emisor = resuelve_rfc_emisor(solicitud, factura)

        resultado, acuse = envia_cancelacion_sw(rfc_emisor, solicitud)
        codigo = str(resultado.get("code"))

        if codigo == CODIGO_SOLICITUD_EXITOSA:
            estatus = ESTATUS_EN_PROCESO
        elif codigo == CODIGO_PREVIAMENTE_CANCELADO:
            estatus = ESTATUS_CANCELADA
        else:
            # Cualquier otro código SAT (205 no existe, 203/204 no corresponde, etc.) es rechazo
            raise CancelacionError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                resultado.get("message") or f"El SAT rechazó la cancelación (código {codigo})",
                {"codigoSat": codigo, "descripcion": resultado.get("description")},
            )

        if factura:
            actualiza_factura(factura["uuid"], estatus, solicitud, resultado, acuse)

        registra_bitacora(solicitud, rfc_emisor, f"{resultado.get('message') or codigo} -> {estatus}", "exito")
        return respuesta(HTTPStatus.OK, {
            "uuid": solicitud["uuid"],
            "estatus": estatus,
            "codigoSat": codigo,
            "mensaje": resultado.get("message"),
            "descripcion": resultado.get("description"),
            "emitidaPorEsteSistema": factura is not None,
            "acuse": acuse,
        })

    except CancelacionError as e:
        registra_bitacora(solicitud, rfc_emisor, f"Rechazada: {e.mensaje}" + (f" | {e.detalle}" if e.detalle else ""), "error")
        cuerpo = {"message": e.mensaje}
        if e.detalle:
            cuerpo["detalle"] = e.detalle
        return respuesta(e.status_code, cuerpo)
    except requests.RequestException as e:
        traceback.print_exc()
        registra_bitacora(solicitud, rfc_emisor, f"Error de comunicación con SW: {e}", "error")
        return respuesta(HTTPStatus.BAD_GATEWAY, {"message": "No se pudo comunicar con el proveedor de timbrado"})
    except Exception as e:
        traceback.print_exc()
        registra_bitacora(solicitud, rfc_emisor, f"Error inesperado: {e}", "error")
        return respuesta(HTTPStatus.INTERNAL_SERVER_ERROR, {"message": "Error interno al procesar la cancelación"})
