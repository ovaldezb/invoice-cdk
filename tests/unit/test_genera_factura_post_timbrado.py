# -*- coding: utf-8 -*-
"""Una factura ya timbrada nunca debe reportarse como error.

El PDF y el correo se generan DESPUES de que el SAT timbro el CFDI. Cuando
alguno de esos pasos fallaba, el except global respondia 500 y el usuario
reintentaba contra un ticket que ya estaba marcado como timbrado: la factura
existia ante el SAT, el folio estaba consumido y no habia forma de recuperar
el PDF ni el correo.
"""
import json
import os
import sys
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_LAMBDAS = Path(__file__).parent.parent.parent / 'invoice_cdk' / 'lambdas'
if str(_LAMBDAS) not in sys.path:
    sys.path.insert(0, str(_LAMBDAS))

# El handler abre MongoClient en tiempo de import. Estas pruebas son unitarias
# puras: no tocan Mongo ni requieren .env_test, asi que se neutraliza la
# conexion antes de importar el modulo.
os.environ.setdefault('MONGODB_URI', 'mongodb://localhost:27017/test')
os.environ.setdefault('DB_NAME', 'test')
with patch('pymongo.MongoClient', return_value=MagicMock()):
    import invoice_cdk.lambdas.genera_factura_handler as handler_module  # noqa: E402

NOMBRE_CON_ENIE = 'MUÑOZ PEÑA JOSÉ ANTONIO'
UUID_TIMBRADO = 'A1B2C3D4-E5F6-7890-ABCD-EF1234567890'

CFDI_TIMBRADO = (
    '<?xml version="1.0"?>'
    '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" '
    'Serie="A" Folio="100" SubTotal="100.00" Total="116.00">'
    f'<cfdi:Receptor Rfc="MUPJ850315AB1" Nombre="{NOMBRE_CON_ENIE}"/>'
    '</cfdi:Comprobante>'
)


def _evento(ticket='TCK-001'):
    return {
        'httpMethod': 'POST',
        'body': json.dumps({
            'timbrado': {
                'Serie': 'A',
                'SubTotal': 100.00,
                'Total': 116.00,
                'Impuestos': {'TotalImpuestosTrasladados': 16.00},
                'Emisor': {'Rfc': 'FAR0010318A1', 'RegimenFiscal': '601'},
                'Receptor': {
                    'Rfc': 'MUPJ850315AB1',
                    'Nombre': NOMBRE_CON_ENIE,
                    'DomicilioFiscalReceptor': '52756',
                    'RegimenFiscalReceptor': '605',
                    'UsoCFDI': 'G03',
                },
            },
            'sucursal': '001',
            'ticket': ticket,
            'idCertificado': '507f1f77bcf86cd799439011',
            'fechaVenta': '2026-08-03T10:00:00',
            'email': 'jose.munoz@ejemplo.mx',
            'direccion': 'AV. INSURGENTES 123',
            'empresa': 'FARZIN',
        })
    }


def _respuesta(payload):
    respuesta = MagicMock()
    respuesta.json.return_value = payload
    return respuesta


@pytest.fixture
def entorno():
    """Aisla las colecciones y los servicios externos del handler."""
    colecciones = {
        nombre: MagicMock() for nombre in
        ('ticket_timbrado_collection', 'folio_collection', 'serie_folio_collection',
         'bitacora_collection', 'facturas_emitidas_collection', 'regimen_fiscal_collection')
    }
    colecciones['folio_collection'].find_one_and_update.return_value = {'noFolio': 100}

    timbrado_ok = _respuesta({
        'status': 'success',
        'data': {
            'cfdi': CFDI_TIMBRADO,
            'uuid': UUID_TIMBRADO,
            'qrCode': '',
            'cadenaOriginalSAT': '||1.1|...||',
            'fechaTimbrado': '2026-08-03T10:00:05',
        }
    })
    token_ok = _respuesta({'data': {'token': 'tok-123'}})

    parches = [patch.object(handler_module, nombre, mock) for nombre, mock in colecciones.items()]
    parches.append(patch.object(handler_module, 'requests'))
    parches.append(patch.object(handler_module, 'get_regimen_fiscal_by_clave', return_value='General de Ley'))
    parches.append(patch.object(handler_module, 'guarda_factura_emitida'))
    parches.append(patch.object(handler_module, 'FacturaEmitida'))
    parches.append(patch.object(handler_module, 'CFDIPDF_FPDF_Generator'))
    parches.append(patch.object(handler_module, 'EmailSender'))
    parches.append(patch.object(handler_module, 'ENVIRONMENT', 'dev'))

    iniciados = [p.start() for p in parches]
    contexto = dict(colecciones)
    contexto['requests'] = iniciados[len(colecciones)]
    contexto['requests'].post.side_effect = [token_ok, timbrado_ok]
    contexto['CFDIPDF_FPDF_Generator'] = iniciados[-3]
    contexto['CFDIPDF_FPDF_Generator'].return_value.generate_pdf.return_value = b'%PDF-1.4 fake'
    contexto['EmailSender'] = iniciados[-2]
    contexto['EmailSender'].return_value.send_invoice.return_value = True

    yield contexto

    for p in parches:
        p.stop()


class TestPasoFeliz:

    def test_devuelve_200_con_uuid_y_pdf(self, entorno):
        respuesta = handler_module.handler(_evento(), None)

        assert respuesta['statusCode'] == HTTPStatus.OK
        cuerpo = json.loads(respuesta['body'])
        assert cuerpo['uuid'] == UUID_TIMBRADO
        assert cuerpo['pdf_cfdi_b64'] is not None
        assert cuerpo['incidencias'] == []

    def test_el_xml_del_correo_declara_utf8(self, entorno):
        handler_module.handler(_evento(), None)

        _, kwargs = entorno['EmailSender'].return_value.send_invoice.call_args
        xml_enviado = kwargs['cfdi_xml']
        assert xml_enviado.splitlines()[0] == '<?xml version="1.0" encoding="UTF-8"?>'
        assert NOMBRE_CON_ENIE in xml_enviado


class TestFallosDespuesDelTimbrado:
    """Ninguno de estos escenarios puede terminar en 500."""

    def test_pdf_roto_no_pierde_la_factura(self, entorno):
        entorno['CFDIPDF_FPDF_Generator'].side_effect = UnicodeEncodeError(
            'latin-1', 'O’BRIEN', 1, 2, 'ordinal not in range(256)')

        respuesta = handler_module.handler(_evento(), None)

        assert respuesta['statusCode'] == HTTPStatus.OK
        cuerpo = json.loads(respuesta['body'])
        assert cuerpo['uuid'] == UUID_TIMBRADO, 'el usuario debe recibir el folio fiscal'
        assert cuerpo['pdf_cfdi_b64'] is None
        assert any('PDF' in incidencia for incidencia in cuerpo['incidencias'])

    def test_pdf_roto_no_libera_el_ticket(self, entorno):
        entorno['CFDIPDF_FPDF_Generator'].side_effect = RuntimeError('logo no encontrado')

        handler_module.handler(_evento(), None)

        entorno['ticket_timbrado_collection'].delete_one.assert_not_called()
        entorno['serie_folio_collection'].delete_one.assert_not_called()

    def test_correo_caido_no_pierde_la_factura(self, entorno):
        entorno['EmailSender'].return_value.send_invoice.side_effect = OSError('SMTP timeout')

        respuesta = handler_module.handler(_evento(), None)

        assert respuesta['statusCode'] == HTTPStatus.OK
        cuerpo = json.loads(respuesta['body'])
        assert cuerpo['uuid'] == UUID_TIMBRADO
        assert cuerpo['pdf_cfdi_b64'] is not None, 'el PDF sigue disponible aunque el correo falle'
        assert any('correo' in incidencia for incidencia in cuerpo['incidencias'])

    def test_correo_rechazado_se_reporta_como_incidencia(self, entorno):
        entorno['EmailSender'].return_value.send_invoice.return_value = False

        cuerpo = json.loads(handler_module.handler(_evento(), None)['body'])

        assert any('correo' in incidencia for incidencia in cuerpo['incidencias'])

    def test_fallo_al_guardar_en_bd_no_pierde_la_factura(self, entorno):
        entorno['facturas_emitidas_collection'].insert_one.side_effect = Exception('mongo caido')
        with patch.object(handler_module, 'guarda_factura_emitida', side_effect=Exception('mongo caido')):
            respuesta = handler_module.handler(_evento(), None)

        assert respuesta['statusCode'] == HTTPStatus.OK
        cuerpo = json.loads(respuesta['body'])
        assert cuerpo['uuid'] == UUID_TIMBRADO
        assert any('BD' in incidencia for incidencia in cuerpo['incidencias'])

    def test_payload_incompleto_al_erp_no_pierde_la_factura(self, entorno):
        """En Prod, una llave faltante al armar el envio al ERP no puede dar 500."""
        evento = _evento()
        cuerpo = json.loads(evento['body'])
        del cuerpo['timbrado']['Impuestos']  # el armado del payload la necesita
        evento['body'] = json.dumps(cuerpo)

        with patch.object(handler_module, 'ENVIRONMENT', 'Prod'):
            respuesta = handler_module.handler(evento, None)

        assert respuesta['statusCode'] == HTTPStatus.OK
        assert json.loads(respuesta['body'])['uuid'] == UUID_TIMBRADO

    def test_erp_no_recibe_nada_si_el_payload_fallo(self, entorno):
        """No se debe intentar el envio ni al principal ni al respaldo sin payload."""
        evento = _evento()
        cuerpo = json.loads(evento['body'])
        del cuerpo['timbrado']['Impuestos']
        evento['body'] = json.dumps(cuerpo)

        with patch.object(handler_module, 'ENVIRONMENT', 'Prod'):
            handler_module.handler(evento, None)

        # Solo las dos llamadas del timbrado (token + issue), ninguna hacia el ERP.
        assert entorno['requests'].post.call_count == 2

    def test_las_incidencias_quedan_en_bitacora(self, entorno):
        entorno['CFDIPDF_FPDF_Generator'].side_effect = RuntimeError('boom')

        handler_module.handler(_evento(), None)

        registrado = entorno['bitacora_collection'].insert_one.call_args[0][0]
        assert registrado['status'] == 'advertencia'
        assert 'timbrada con incidencias' in registrado['mensaje']


class TestErroresAntesDelTimbrado:
    """El except global ya no puede reventar por su cuenta."""

    def test_body_sin_llaves_devuelve_500_con_mensaje(self, entorno):
        evento = {'httpMethod': 'POST', 'body': json.dumps({'ticket': 'TCK-002'})}

        respuesta = handler_module.handler(evento, None)

        assert respuesta['statusCode'] == HTTPStatus.INTERNAL_SERVER_ERROR
        assert json.loads(respuesta['body'])['message'], 'el mensaje no puede venir vacio'

    def test_body_malformado_devuelve_500_con_mensaje(self, entorno):
        evento = {'httpMethod': 'POST', 'body': '{esto no es json'}

        respuesta = handler_module.handler(evento, None)

        assert respuesta['statusCode'] == HTTPStatus.INTERNAL_SERVER_ERROR
        assert json.loads(respuesta['body'])['message']

    def test_error_previo_se_registra_en_bitacora_sin_reventar(self, entorno):
        handler_module.handler({'httpMethod': 'POST', 'body': '{roto'}, None)

        registrado = entorno['bitacora_collection'].insert_one.call_args[0][0]
        assert registrado['status'] == 'error'
        assert registrado['ticket'] is None
        assert registrado['rfc'] is None
