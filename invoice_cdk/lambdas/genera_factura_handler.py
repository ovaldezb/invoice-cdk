import base64
from http import HTTPStatus
import os
import json
import traceback
import requests
import xml.dom.minidom
from cfdi_pdf_fpdf_generator import CFDIPDF_FPDF_Generator
from constantes import Constants
from pymongo import MongoClient
from dbaccess.db_datos_factura import (get_regimen_fiscal_by_clave)
from dbaccess.db_factura import (guarda_factura_emitida, get_factura_by_ticket)
from models.factura_emitida import FacturaEmitida
from email_sender import EmailSender
from datetime import datetime, timezone, timedelta

SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")
ENVIRONMENT = os.getenv("ENV")
USER_NAME_CLIENT = os.getenv("TAPETES_USER_NAME")
PASSWORD_CLIENT = os.getenv("TAPETES_PASSWORD")
TAPETES_API_URL = os.getenv("TAPETES_API_URL")
TAPETES_API_URL_BACKUP = os.getenv("TAPETES_API_URL_BACKUP")

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
facturas_emitidas_collection = db["facturasemitidas"]
regimen_fiscal_collection = db["regimenfiscal"]
folio_collection = db["folios"]
ticket_timbrado_collection = db["ticket_timbrado"]
serie_folio_collection = db["serie_folio"]
bitacora_collection = db["bitacora"]

APPLICATION_JSON = "application/json"
headersEndpoint = {
    'Content-Type': 'application/x-www-form-urlencoded',
}
headers = {
    "Content-Type": APPLICATION_JSON,
    "Access-Control-Allow-Origin": "*"
}


def registra_bitacora(ticket, timbrado, email_receptor, mensaje, status, incluir_traceback=False):
    """Escribe en bitacora sin poder tumbar el flujo principal.

    Las variables llegan posiblemente vacias (si el error ocurrio antes de
    parsear el body), por eso se accede al timbrado de forma defensiva.
    """
    try:
        receptor = (timbrado or {}).get('Receptor', {})
        emisor = (timbrado or {}).get('Emisor', {})
        bitacora_collection.insert_one({
            "ticket": ticket,
            "rfc": receptor.get('Rfc'),
            "rfcEmisor": emisor.get('Rfc'),
            "email": email_receptor,
            "mensaje": mensaje,
            "status": status,
            "traceback": traceback.format_exc() if incluir_traceback else '',
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        })
    except Exception:
        print("No se pudo escribir en bitacora")
        traceback.print_exc()


def handler(event, context):
    # Inicializadas antes del try: el except global las usa y si el error ocurre
    # al parsear el body (JSON malformado, llave faltante) reventaba con NameError
    # dentro del propio except, devolviendo un 502 sin cuerpo.
    ticket = None
    timbrado = {}
    email_receptor = None
    try:
        http_method = event["httpMethod"]
        body = json.loads(event.get("body"))
        timbrado = body['timbrado']
        sucursal = body['sucursal']
        ticket = body['ticket'] 
        id_certificado = body['idCertificado']
        fecha_venta = body['fechaVenta']
        email_receptor = body['email']
        direccion = body['direccion']
        empresa = body['empresa']
        #buscar el ID del usuario que viene en el CSD, para despues asignarlo en la bitacora
        if http_method == Constants.POST:
            #Estos son los pasos para generar la factura
            #0 revisar si ya existe la factura para el ticket
            try:
                ticket_timbrado_collection.insert_one({"ticket": ticket.replace("-", ""), "fechaTimbrado": datetime.now(timezone.utc).isoformat()})
            except Exception as e:
                registra_bitacora(ticket, timbrado, email_receptor,
                                  "ya existe una solicitud de timbrado para el ticket",
                                  "error", incluir_traceback=True)
                return {
                    "statusCode": 500,
                    "headers": headers,
                    "body": json.dumps({"message": f"Ya existe una solicitud de timbrado para el ticket: {ticket}"})
                }
            #1. Obtener el folio actual y actualizarlo, para evitar colisiones
            folio = folio_collection.find_one_and_update({"sucursal": sucursal}, {"$inc": {"noFolio": 1}}, return_document=False)
            #2. Asignar el folio al timbrado
            if not folio:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"message": f"No se encontró folio para la sucursal {sucursal}, favor contactar al administador"})
                }
            timbrado['Folio'] = folio['noFolio']
            folio_flag=True
            while folio_flag:
                try:
                    serie_folio_collection.insert_one({"folioTimbrado": timbrado['Serie'] + str(folio['noFolio'])})
                    folio_flag=False
                except Exception as e:
                    folio = folio_collection.find_one_and_update({"sucursal": sucursal}, {"$inc": {"noFolio": 1}}, return_document=False)
                    timbrado['Folio'] = folio['noFolio']
            #2.1 obtener el regimen fiscal del emisor
            regimen_fiscal_emisor = get_regimen_fiscal_by_clave(timbrado['Emisor']['RegimenFiscal'],regimen_fiscal_collection)
            regimen_fiscal_receptor = get_regimen_fiscal_by_clave(timbrado['Receptor']['RegimenFiscalReceptor'],regimen_fiscal_collection)
            
            #3. Obtener el token de SW Sapiens
            sw_token = requests.post(
                f"{SW_URL}/v2/security/authenticate",
                headers={"Content-Type": APPLICATION_JSON},
                data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
            ).json()
            #4. Enviar el timbrado a SW Sapiens
            factura_generada = requests.post(
                f"{SW_URL}/v3/cfdi33/issue/json/v4",
                headers={"Content-Type": "application/jsontoxml","Authorization": f"Bearer {sw_token.get('data').get('token')}"},  # Fixed token extraction
                data=json.dumps(timbrado)
            ).json()
            print(factura_generada)
            #4.1 Validar si hubo error en la generación de la factura
            if factura_generada.get("status") == 'error':
                #revisar este punto si se debe decrementar el folio
                serie_folio_collection.delete_one({"folioTimbrado": timbrado['Serie'] + str(folio['noFolio'])})
                folio_collection.find_one_and_update({"sucursal": sucursal}, {"$inc": {"noFolio": -1}}, return_document=False)
                ticket_timbrado_collection.delete_one({"ticket": ticket.replace("-", "")})
                receptor_timbrado = timbrado.get('Receptor', {})
                registra_bitacora(ticket, timbrado, email_receptor,
                                  "Nombre:" + str(receptor_timbrado.get('Nombre', '')) +
                                  " CP:" + str(receptor_timbrado.get('DomicilioFiscalReceptor', '')) +
                                  " Reg Fis:" + str(regimen_fiscal_receptor) +
                                  " Uso CFDI:" + str(receptor_timbrado.get('UsoCFDI', '')) +
                                  " " + str(factura_generada.get("message")),
                                  "error")
                return {
                    Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({"message": factura_generada.get("message")})
                }
            #5. Formatear el XML para que se retornarlo al endpoint del cliente
            # Se declara encoding="UTF-8" explicitamente: sin la declaracion, los
            # consumidores que asumen la codificacion local (cp1252/latin-1) leen mal
            # los nombres con enie o acentos. El formato del documento no cambia,
            # solo se agrega la declaracion en la primera linea.
            dom = xml.dom.minidom.parseString(factura_generada["data"]["cfdi"])
            pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")
            xml_escaped = pretty_xml.replace('"',r'\"')
            
            body_envio_endpoint = None
            if(ENVIRONMENT == 'Prod'):
            #5.1 preparar el body para enviar al endpoint
            # El armado va dentro del try: una llave faltante aqui reventaba con
            # KeyError hacia el except global y devolvia 500 con el CFDI ya timbrado.
                try:
                    body_envio_endpoint=json.dumps({
                                "erfc"     : timbrado['Emisor']['Rfc'],
                                "sucursal" : sucursal,
                                "serie"    : timbrado['Serie'],
                                "folio"    : str(timbrado['Folio']),
                                "subtotal" : str(timbrado['SubTotal']),
                                "impuesto" : str(timbrado['Impuestos']['TotalImpuestosTrasladados']),
                                "total"    : str(timbrado['Total']),
                                "uuid"     : factura_generada["data"]["uuid"],
                                "rrfc"     : timbrado['Receptor']['Rfc'],
                                "rnombre"  : timbrado['Receptor']['Nombre'],
                                "ruso"     : timbrado['Receptor']['UsoCFDI'],
                                "rregimen" : timbrado['Receptor']['RegimenFiscalReceptor'],
                                "rcp"      : timbrado['Receptor']['DomicilioFiscalReceptor'],
                                "tickets"  : ticket,
                                "fecha"    : factura_generada.get("data").get("fechaTimbrado"),
                                "servicio" : "ChipoSoft Corp.",
                                "xml_cfdi" : pretty_xml,
                                "xml_cfdi_b64" : base64.b64encode(xml_escaped.encode()).decode()
                                })
                    print(body_envio_endpoint)
                except Exception as e:
                    traceback.print_exc()
                    body_envio_endpoint = None
                    registra_bitacora(ticket, timbrado, email_receptor,
                                      f"No se pudo armar el envio al ERP: {e}", "advertencia",
                                      incluir_traceback=True)
            #5.2 Obtener el token del endpoint del cliente (Tapetes)
            if(ENVIRONMENT == 'Prod' and body_envio_endpoint):
                try:
                    form_data = {
                        "username": USER_NAME_CLIENT,
                        "password": PASSWORD_CLIENT
                    }
                    response = requests.post(
                        f"{TAPETES_API_URL}token", 
                        headers=headersEndpoint, 
                        data=form_data
                    )
                    token = response.json().get("access_token")            
                    requests.post(
                        f"{TAPETES_API_URL}recibefacturas/",
                        headers={"Accept": APPLICATION_JSON, "Content-Type": APPLICATION_JSON, "Authorization": f"Bearer {token}"},
                        data=body_envio_endpoint
                    )
                    print(f"Factura enviada al url: {TAPETES_API_URL}")
                except Exception as e:
                    print(f"Error al enviar factura a tapetes: {e}")
                    print(f"Se enviara al 2do Endpoint {TAPETES_API_URL_BACKUP}")
                    try:
                        form_data = {
                            "username": USER_NAME_CLIENT,
                            "password": PASSWORD_CLIENT
                        }
                        response_backup = requests.post(
                            f"{TAPETES_API_URL_BACKUP}token", 
                            headers=headersEndpoint, 
                            data=form_data
                        )
                        token_backup = response_backup.json().get("access_token")
                        requests.post(
                            f"{TAPETES_API_URL_BACKUP}recibefacturas/",
                            headers={"Accept": APPLICATION_JSON, "Content-Type": APPLICATION_JSON, "Authorization": f"Bearer {token_backup}"},
                            data=body_envio_endpoint
                        )
                        print(f"Factura enviada al url de respaldo: {TAPETES_API_URL_BACKUP}")
                    except Exception as e:
                        traceback.print_exc()
                        registra_bitacora(ticket, timbrado, email_receptor,
                                          f"Error: {str(e)}", "error", incluir_traceback=True)
                        print(f"Error al enviar factura al endpoint de respaldo: {e}")

            # ------------------------------------------------------------------
            # PUNTO DE NO RETORNO: el CFDI ya esta timbrado ante el SAT.
            # A partir de aqui ningun fallo puede devolver 500 ni liberar el
            # ticket: hacerlo dejaba la factura timbrada, el folio consumido y
            # al usuario reintentando contra "ya existe una solicitud de
            # timbrado". Cada paso se aisla y se reporta como exito parcial.
            # ------------------------------------------------------------------
            uuid = factura_generada["data"]["uuid"]
            incidencias = []

            #6. Guardar la factura generada en la base de datos
            factura_generada["data"]["sucursal"]=sucursal
            factura_generada["data"]["idCertificado"]=id_certificado
            factura_generada["data"]["ticket"]=ticket
            factura_generada["data"]["estatus"]="Vigente"
            try:
                guarda_factura_emitida(FacturaEmitida(**factura_generada["data"]), facturas_emitidas_collection)
            except Exception as e:
                traceback.print_exc()
                incidencias.append(f"No se guardo la factura en BD: {e}")

            #7 Generar PDF de la factura
            pdf_b64 = None
            try:
                cfdi = factura_generada["data"]["cfdi"]
                qr_code = factura_generada["data"]["qrCode"]
                cadena_original_sat = factura_generada["data"]["cadenaOriginalSAT"]
                pdf_bytes = CFDIPDF_FPDF_Generator(cfdi, qr_code, cadena_original_sat, ticket, fecha_venta,direccion,empresa,regimen_fiscal_emisor, regimen_fiscal_receptor).generate_pdf()
                pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
            except Exception as e:
                traceback.print_exc()
                incidencias.append(f"No se genero el PDF: {e}")

            #8. Envia correo
            if email_receptor and "@" in email_receptor:
                try:
                    email = EmailSender()
                    result = email.send_invoice(
                        recipient_email=email_receptor,
                        pdf_base64=pdf_b64,
                        cfdi_xml=pretty_xml,
                        pdf_filename=f"{uuid}.pdf",
                        xml_filename=f"{uuid}.xml",
                        subject="Factura del ticket " + ticket,
                        body_text="Se adjunto factura en PDF y XML para el ticket " + ticket+" \n Agradecemos su preferencia"
                    )
                    print(f"Email sent: {result}")
                    if not result:
                        incidencias.append("No se pudo enviar el correo al receptor")
                except Exception as e:
                    traceback.print_exc()
                    incidencias.append(f"No se pudo enviar el correo: {e}")

            #9. Retornar la factura generada a la página
            detalle_folio = " Serie:" + str(timbrado.get('Serie', '')) + " folio:" + str(timbrado.get('Folio', ''))
            if incidencias:
                registra_bitacora(ticket, timbrado, email_receptor,
                                  "Factura timbrada con incidencias posteriores" + detalle_folio + " | " + " | ".join(incidencias),
                                  "advertencia")
            else:
                registra_bitacora(ticket, timbrado, email_receptor,
                                  "Factura generada exitosamente" + detalle_folio, "exito")
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({
                    **factura_generada["data"],
                    "pdf_cfdi_b64": pdf_b64,
                    "incidencias": incidencias
                    })
            }
        elif http_method == Constants.PUT:
            uuid = body['uuid']
            rfc = body['rfc']
            motivo = body['motivo']
            #3. Obtener el token de SW Sapiens
            sw_token = requests.post(
                f"{SW_URL}/v2/security/authenticate",
                headers={"Content-Type": APPLICATION_JSON},
                data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
            ).json()
            #4. Enviar la solicitud de cancelación a SW Sapiens
            respuesta = factura_generada = requests.post(
                f"{SW_URL}/cfdi33/cancel/{rfc}/{uuid}/{motivo}",
                headers={"Authorization": f"Bearer {sw_token.get('data').get('token')}"},  # Fixed token extraction
            ).json()
            print(f"Respuesta cancelacion: {respuesta}")
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps(respuesta)
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        registra_bitacora(ticket, timbrado, email_receptor,
                          f"Error: {str(e)}", "error", incluir_traceback=True)
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.HEADERS_KEY: headers,
            Constants.BODY: json.dumps({"message": str(e)})
        }