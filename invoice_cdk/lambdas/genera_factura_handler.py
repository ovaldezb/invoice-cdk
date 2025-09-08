import base64
import os
import json
import traceback
import requests
import xml.dom.minidom
from cfdi_pdf_fpdf_generator import CFDIPDF_FPDF_Generator
from pymongo import MongoClient
from db_datos_factura import guarda_factura_emitida
from factura_emitida import FacturaEmitida


SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")
USER_NAME_CLIENT = os.getenv("TAPETES_USER_NAME")
PASSWORD_CLIENT = os.getenv("TAPETES_PASSWORD")
tapetes_api_url = os.getenv("TAPETES_API_URL")

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
facturas_emitidas_collection = db["facturasemitidas"]
folio_collection = db["folios"]

APPLICATION_JSON = "application/json"
headersEndpoint = {
    'Content-Type': 'application/x-www-form-urlencoded',
}
headers = {
    "Content-Type": APPLICATION_JSON,
    "Access-Control-Allow-Origin": "*"
}


def handler(event, context):
    try:
        http_method = event["httpMethod"]
        body = json.loads(event.get("body"))
        timbrado = body['timbrado']
        sucursal = body['sucursal']
        ticket = body['ticket'] 
        id_certificado = body['idCertificado']
        fecha_venta = body['fechaVenta']
        
        if http_method == "POST":
            #Estos son los pasos para generar la factura
            #1. Obtener el folio actual y actualizarlo, para evitar colisiones
            folio = folio_collection.find_one_and_update({"sucursal": sucursal}, {"$inc": {"noFolio": 1}}, return_document=True)
            #2. Asignar el folio al timbrado
            if not folio:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"message": f"No se encontró folio para la sucursal {sucursal}, favor contactar al administador"})
                }
            timbrado['Folio'] = folio['noFolio']
            #3. Obtener el token de SW
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
            #4.1 Validar si hubo error en la generación de la factura
            if factura_generada.get("status") == 'error':
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"message": factura_generada.get("message")})
                }
            #5. Formatear el XML para que se retornarlo al endpoint del cliente
            dom = xml.dom.minidom.parseString(factura_generada["data"]["cfdi"])
            pretty_xml = dom.toprettyxml(indent="  ")
            xml_escaped = pretty_xml.replace('"',r'\"')
            
            #5.1 Obtener el token del endpoint del cliente (Tapetes)
            form_data = {
                "username": USER_NAME_CLIENT,
                "password": PASSWORD_CLIENT
            }
            response = requests.post(
                f"{tapetes_api_url}token", 
                headers=headersEndpoint, 
                data=form_data
            )
            token = response.json().get("access_token")
            #5.2 Enviar la factura generada al endpoint del cliente (Tapetes)
            body_envio_endpoint=json.dumps({
                                "erfc"     : timbrado['Emisor']['Rfc'],
                                "sucursal" : sucursal,
                                "serie"    : timbrado['Serie'],
                                "folio"    : timbrado['Folio'],
                                "subtotal" : timbrado['SubTotal'],
                                "impuesto" : timbrado['Impuestos']['TotalImpuestosTrasladados'],
                                "total"    : timbrado['Total'],
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
            
            requests.post(
                f"{tapetes_api_url}recibefacturas/",
                headers={"Accept": APPLICATION_JSON, "Content-Type": APPLICATION_JSON, "Authorization": f"Bearer {token}"},
                data=body_envio_endpoint
            )
            #6. Guardar la factura generada en la base de datos
            factura_generada["data"]["sucursal"]=sucursal
            factura_generada["data"]["idCertificado"]=id_certificado
            guarda_factura_emitida(FacturaEmitida(**factura_generada["data"]), facturas_emitidas_collection)
            #7 Generar PDF de la factura
            
            cfdi = factura_generada["data"]["cfdi"]
            qrCode = factura_generada["data"]["qrCode"]
            cadena_original_sat = factura_generada["data"]["cadenaOriginalSAT"]
            print(f'Factura generada: {cfdi}')
            print(f'QR Code: {qrCode}')
            pdf_bytes = CFDIPDF_FPDF_Generator(cfdi, qrCode,cadena_original_sat,ticket,fecha_venta).generate_pdf()
            pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
            #8. Retornar la factura generada a la página
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    **factura_generada["data"],
                    "pdf_cfdi_b64": pdf_b64
                    })
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()