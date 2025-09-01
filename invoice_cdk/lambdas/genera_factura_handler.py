import base64
import os
import json
import requests
import xml.dom.minidom
from pymongo import MongoClient
from db_datos_factura import guarda_factura_emitida
from factura_emitida import FacturaEmitida

SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")
USER_NAME_CLIENT = os.getenv("USER_NAME")
PASSWORD_CLIENT = os.getenv("PASSWORD")
tapetes_api_url = os.getenv("TAPETES_API_URL")

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
facturas_emitidas_collection = db["facturasemitidas"]

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
        id_sucursal = body['idSucursal']

        if http_method == "POST":
            sw_token = requests.post(
                f"{SW_URL}/v2/security/authenticate",
                headers={"Content-Type": APPLICATION_JSON},
                data=json.dumps({"user": SW_USER_NAME, "password": SW_USER_PASSWORD})
            ).json()
            
            factura_generada = requests.post(
                f"{SW_URL}/v3/cfdi33/issue/json/v4",
                headers={"Content-Type": "application/jsontoxml","Authorization": f"Bearer {sw_token.get('data').get('token')}"},  # Fixed token extraction
                data=json.dumps(timbrado)
            ).json()
            
            dom = xml.dom.minidom.parseString(factura_generada["data"]["cfdi"])
            pretty_xml = dom.toprettyxml(indent="  ")
            xml_escaped = pretty_xml.replace('"',r'\"')
            
            #aqui voy a enviar la respuesta al endpoint del cliente
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
                                "tickets"  : [ticket],
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
            factura_generada["data"]["sucursal"]=sucursal
            factura_generada["data"]["idSucursal"]=id_sucursal

            factura_emitida_id = guarda_factura_emitida(FacturaEmitida(**factura_generada["data"]), facturas_emitidas_collection).inserted_id
            print(f"Factura emitida guardada con ID: {factura_emitida_id}")
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(factura_generada)
            }

    except Exception as e:
        print(f"Error: {str(e)}")