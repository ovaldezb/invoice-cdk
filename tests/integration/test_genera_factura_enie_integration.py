# -*- coding: utf-8 -*-
"""Timbrado real (sandbox SW Sapiens) con un receptor cuyo nombre lleva enie.

Reproduce el escenario reportado en produccion: un receptor con enie y acentos
en la razon social. Antes de la correccion, el XML salia sin declaracion de
codificacion hacia el correo y hacia el ERP, y el PDF podia reventar.

COMO EJECUTARLO
---------------
Requiere .env_test con credenciales del sandbox (el pipeline lo inyecta):

    SW_URL, SW_USER_NAME, SW_USER_PASSWORD   -> sandbox de SW Sapiens
    MONGODB_URI, DB_NAME                     -> base de pruebas
    ENV=test                                 -> evita el envio al ERP de Tapetes

Opcionalmente, para probar tambien un RFC que contenga enie:

    RFC_RECEPTOR_ENIE=<RFC de pruebas con enie, dado de alta en el sandbox>

Si no se define, se usa el RFC de pruebas habitual y la enie se ejercita en el
nombre, que es donde vive el defecto (XML, PDF y correo).

    pytest tests/integration/test_genera_factura_enie_integration.py -v -s
"""
import os
from pathlib import Path

# Cargar variables de entorno ANTES de importar cualquier handler
env_file = Path(__file__).parent.parent.parent / '.env_test'
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key not in os.environ:
                    os.environ[key] = value.strip('"').strip("'")
else:
    raise FileNotFoundError(f"Required .env_test file not found at {env_file}")

_lambdas_dir = Path(__file__).parent.parent.parent / 'invoice_cdk' / 'lambdas'

import base64  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import time  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402
from http import HTTPStatus  # noqa: E402

import pytest  # noqa: E402
from bson import ObjectId  # noqa: E402
from pymongo import MongoClient  # noqa: E402

import invoice_cdk.lambdas.genera_factura_handler as genera_factura_handler  # noqa: E402

# Receptor de prueba: enie en ambos apellidos y acento en el nombre.
NOMBRE_RECEPTOR = 'JOSE ANTONIO MUÑOZ PEÑA'
RFC_RECEPTOR = os.environ.get('RFC_RECEPTOR_ENIE', 'EELD880811EJ6')
SUCURSAL_PRUEBA = '182'
SERIE_PRUEBA = 'OSFI'


@pytest.fixture(scope='module')
def directorio_lambdas():
    """El generador de PDF busca los logos en su propio directorio."""
    original = os.getcwd()
    os.chdir(_lambdas_dir)
    yield
    os.chdir(original)


@pytest.fixture(scope='module')
def colecciones(directorio_lambdas):
    uri = os.environ.get('MONGODB_URI')
    nombre_db = os.environ.get('DB_NAME')
    if not uri or not nombre_db:
        pytest.skip('MONGODB_URI y DB_NAME son obligatorios para pruebas de integracion')
    cliente = MongoClient(uri)
    db = cliente[nombre_db]
    yield {
        'facturas_emitidas': db['facturasemitidas'],
        'regimen_fiscal': db['regimenfiscal'],
        'folios': db['folios'],
        'ticket_timbrado': db['ticket_timbrado'],
        'serie_folio': db['serie_folio'],
        'bitacora': db['bitacora'],
    }
    cliente.close()


@pytest.fixture
def datos_prueba(colecciones):
    ticket = f"TENIE{int(time.time() * 1000) % 10000000}-{random.randint(1000, 9999)}"
    print(f"\n🎫 Ticket de prueba: {ticket}")

    colecciones['regimen_fiscal'].update_one(
        {"regimenfiscal": "601"},
        {"$set": {"regimenfiscal": "601", "descripcion": "General de Ley Personas Morales"}},
        upsert=True)
    colecciones['regimen_fiscal'].update_one(
        {"regimenfiscal": "612"},
        {"$set": {"regimenfiscal": "612",
                  "descripcion": "Personas Físicas con Actividades Empresariales y Profesionales"}},
        upsert=True)
    colecciones['folios'].update_one(
        {"sucursal": SUCURSAL_PRUEBA},
        {"$set": {"sucursal": SUCURSAL_PRUEBA, "noFolio": 1000}},
        upsert=True)

    folio_actual = colecciones['folios'].find_one({"sucursal": SUCURSAL_PRUEBA})['noFolio']

    yield {'ticket': ticket, 'sucursal': SUCURSAL_PRUEBA, 'folio': folio_actual,
           'certificado_id': str(ObjectId())}

    colecciones['ticket_timbrado'].delete_many({"ticket": ticket.replace("-", "")})
    colecciones['ticket_timbrado'].delete_many({"ticket": ticket})
    colecciones['serie_folio'].delete_many({"folioTimbrado": {"$regex": f"^{SERIE_PRUEBA}"}})
    colecciones['facturas_emitidas'].delete_many({"ticket": ticket})
    colecciones['bitacora'].delete_many({"ticket": ticket})


def _construye_evento(datos):
    # Montos unicos: SW Sapiens detecta duplicados por RFC + fecha + importes.
    base = 24000.00 + (int(time.time()) % 10000) / 100
    iva = round(base * 0.16, 2)
    total = round(base + iva, 2)

    timbrado = {
        "Version": "4.0",
        "Serie": SERIE_PRUEBA,
        "Folio": "",
        "Fecha": "2025-11-25T10:00:00",
        "FormaPago": "04",
        "CondicionesDePago": "Un solo pago",
        "SubTotal": base,
        "Descuento": 0,
        "Moneda": "MXN",
        "TipoCambio": 1,
        "Total": total,
        "TipoDeComprobante": "I",
        "Exportacion": "01",
        "MetodoPago": "PUE",
        "LugarExpedicion": "05109",
        "Emisor": {"Rfc": "FAR0010318A1", "Nombre": "FARZIN", "RegimenFiscal": "601"},
        "Receptor": {
            "Rfc": RFC_RECEPTOR,
            "Nombre": NOMBRE_RECEPTOR,
            "DomicilioFiscalReceptor": "01180",
            "RegimenFiscalReceptor": "612",
            "UsoCFDI": "G03",
        },
        "Conceptos": [{
            "Impuestos": {"Traslados": [{"Base": base, "Impuesto": "002", "TipoFactor": "Tasa",
                                         "TasaOCuota": "0.160000", "Importe": iva}]},
            "ClaveProdServ": "56101500",
            "Cantidad": 1,
            "ClaveUnidad": "H87",
            "Unidad": "Pieza",
            # Descripcion con acentos: tambien viaja al PDF.
            "Descripcion": "TAPETE ARTESANAL DISEÑO ESPAÑOL 3.10 X 2.16",
            "ValorUnitario": base,
            "Importe": base,
            "Descuento": 0,
            "ObjetoImp": "02",
        }],
        "Impuestos": {
            "Traslados": [{"Base": base, "Impuesto": "002", "TipoFactor": "Tasa",
                           "TasaOCuota": "0.160000", "Importe": iva}],
            "TotalImpuestosTrasladados": iva,
        },
    }

    return {
        "httpMethod": "POST",
        "body": json.dumps({
            "timbrado": timbrado,
            "sucursal": datos['sucursal'],
            "ticket": datos['ticket'],
            "idCertificado": datos['certificado_id'],
            "fechaVenta": "2025-11-25T10:00:00",
            "email": "pruebas.enie@example.com",
            "direccion": "AV. ESPAÑA 123, COL. NIÑOS HÉROES, CDMX",
            "empresa": "FARZIN",
        }),
        "headers": {"Content-Type": "application/json", "origin": "http://localhost:4200"},
    }


class TestTimbradoConEnie:

    @pytest.fixture(scope='class', autouse=True)
    def valida_credenciales(self):
        if not os.environ.get('SW_URL') or not os.environ.get('SW_USER_NAME'):
            pytest.skip('SW_URL y SW_USER_NAME son obligatorios: sin sandbox no hay timbrado real')
        if os.environ.get('ENV') == 'Prod':
            pytest.fail('Esta prueba NUNCA debe correr con ENV=Prod: enviaria al ERP real')

    @pytest.fixture(scope='class')
    def resultado(self, request, colecciones):
        """Timbra una sola vez y comparte el resultado con todas las aserciones."""
        datos = request.getfixturevalue('datos_prueba')
        respuesta = genera_factura_handler.handler(_construye_evento(datos), None)
        print(f"\n📄 statusCode: {respuesta['statusCode']}")
        return {'respuesta': respuesta, 'datos': datos}

    def test_el_timbrado_es_exitoso(self, resultado):
        respuesta = resultado['respuesta']
        cuerpo = json.loads(respuesta['body'])
        assert respuesta['statusCode'] == HTTPStatus.OK, f"SW rechazo el timbrado: {cuerpo}"
        assert cuerpo.get('uuid'), 'debe regresar folio fiscal'

    def test_no_hubo_incidencias_posteriores(self, resultado):
        """Si el PDF o el correo fallaron, aqui se ve explicitamente."""
        cuerpo = json.loads(resultado['respuesta']['body'])
        assert cuerpo.get('incidencias') == [], f"incidencias: {cuerpo.get('incidencias')}"

    def test_el_cfdi_conserva_la_enie(self, resultado):
        cuerpo = json.loads(resultado['respuesta']['body'])
        cfdi = cuerpo['cfdi']

        raiz = ET.fromstring(cfdi)
        receptor = raiz.find('{http://www.sat.gob.mx/cfd/4}Receptor')
        assert receptor.attrib['Nombre'] == NOMBRE_RECEPTOR
        assert 'Ñ' in receptor.attrib['Nombre']

    def test_el_pdf_se_genero(self, resultado):
        """Con nombre y descripcion acentuados, el PDF ya no revienta."""
        cuerpo = json.loads(resultado['respuesta']['body'])
        assert cuerpo.get('pdf_cfdi_b64'), 'el PDF debe venir en la respuesta'

        pdf_bytes = base64.b64decode(cuerpo['pdf_cfdi_b64'])
        assert pdf_bytes.startswith(b'%PDF'), 'debe ser un PDF valido'
        assert len(pdf_bytes) > 5000, 'un PDF de factura completo pesa mas que esto'

    def test_la_factura_quedo_en_bd_con_la_enie(self, resultado, colecciones):
        guardada = colecciones['facturas_emitidas'].find_one({"ticket": resultado['datos']['ticket']})
        assert guardada is not None, 'la factura debe quedar registrada'
        assert 'Ñ' in guardada['cfdi'], 'la enie debe sobrevivir el viaje a Mongo'

    def test_la_bitacora_registra_exito(self, resultado, colecciones):
        registro = colecciones['bitacora'].find_one({"ticket": resultado['datos']['ticket']})
        assert registro is not None
        assert registro['status'] == 'exito', f"bitacora: {registro.get('mensaje')}"


class TestXmlEntregadoAlCliente:
    """El XML que sale hacia el correo y hacia el ERP debe declarar su codificacion."""

    def test_el_pretty_xml_declara_utf8(self):
        """Verifica la transformacion exacta que aplica el handler, sin salir a la red."""
        import xml.dom.minidom

        cfdi = (
            '<?xml version="1.0"?>'
            '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Total="116.00">'
            f'<cfdi:Receptor Rfc="{RFC_RECEPTOR}" Nombre="{NOMBRE_RECEPTOR}"/>'
            '</cfdi:Comprobante>'
        )
        dom = xml.dom.minidom.parseString(cfdi)
        pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

        assert pretty_xml.splitlines()[0] == '<?xml version="1.0" encoding="UTF-8"?>'
        assert NOMBRE_RECEPTOR in pretty_xml

        # El ERP sigue recibiendo el mismo escapado de comillas de siempre.
        xml_escaped = pretty_xml.replace('"', r'\"')
        recuperado = base64.b64decode(base64.b64encode(xml_escaped.encode())).decode()
        assert 'MUÑOZ PEÑA' in recuperado
        assert r'encoding=\"UTF-8\"' in recuperado
