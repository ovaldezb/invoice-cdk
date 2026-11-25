"""
Unit tests for timbrado_xml_handler (POST /timbrado-xml).
Usan mocks: no requieren base de datos ni acceso a SW.
"""
import base64
import json
from unittest.mock import MagicMock, patch

import pytest

RFC_EMISOR = "EKU9003173C9"


def cfdi(version="4.0", sello="SELLO==", no_cert="30001000000500003416", cert="MIIF==", rfc_emisor=RFC_EMISOR,
         ns="http://www.sat.gob.mx/cfd/4"):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<cfdi:Comprobante xmlns:cfdi="{ns}" Version="{version}" Serie="PS" Folio="100" '
        'Fecha="2026-11-25T11:52:09" Moneda="MXN" FormaPago="28" LugarExpedicion="04500" MetodoPago="PUE" '
        'SubTotal="100.00" Total="116.00" TipoDeComprobante="I" Exportacion="01" '
        f'NoCertificado="{no_cert}" Certificado="{cert}" Sello="{sello}">'
        f'<cfdi:Emisor Rfc="{rfc_emisor}" Nombre="ESCUELA KEMPER URGATE" RegimenFiscal="601"/>'
        '<cfdi:Receptor Rfc="XAXX010101000" Nombre="PUBLICO EN GENERAL" DomicilioFiscalReceptor="04500" '
        'UsoCFDI="S01" RegimenFiscalReceptor="616"/>'
        '<cfdi:Conceptos><cfdi:Concepto ClaveProdServ="52101509" Cantidad="1" ClaveUnidad="H87" '
        'Descripcion="TAPETE" ValorUnitario="100.00" Importe="100.00" ObjetoImp="02"/></cfdi:Conceptos>'
        '</cfdi:Comprobante>'
    )


DATA_TIMBRADO = {
    "cadenaOriginalSAT": "||1.1|...||",
    "noCertificadoSAT": "30001000000500003456",
    "noCertificadoCFDI": "30001000000500003416",
    "uuid": "8E0B7B45-1E2A-4C0B-9F2E-1C2D3E4F5A6B",
    "selloSAT": "SAT==",
    "selloCFDI": "SELLO==",
    "fechaTimbrado": "2026-11-25T11:52:30",
    "qrCode": "QR==",
    "cfdi": "<cfdi:Comprobante ...>",
}


@pytest.fixture
def h():
    import invoice_cdk.lambdas.timbrado_xml_handler as handler_module
    handler_module.certificates_collection = MagicMock()
    handler_module.bitacora_collection = MagicMock()
    handler_module.SW_URL = "https://sw.test"
    handler_module.certificates_collection.find_one.return_value = {"rfc": RFC_EMISOR}
    return handler_module


def evento(xml, base64_encoded=False):
    if base64_encoded:
        return {"httpMethod": "POST", "body": base64.b64encode(xml.encode()).decode(), "isBase64Encoded": True}
    return {"httpMethod": "POST", "body": xml, "isBase64Encoded": False}


def respuesta_token():
    resp = MagicMock()
    resp.json.return_value = {"data": {"token": "tok"}, "status": "success"}
    return resp


def respuesta_sw(cuerpo):
    resp = MagicMock()
    resp.json.return_value = cuerpo
    return resp


class TestTimbradoExitoso:
    @patch("invoice_cdk.lambdas.timbrado_xml_handler.requests.post")
    def test_timbra_y_regresa_datos(self, mock_post, h):
        mock_post.side_effect = [respuesta_token(), respuesta_sw({"data": DATA_TIMBRADO, "status": "success"})]

        r = h.handler(evento(cfdi()), {})

        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["status"] == "success"
        assert body["uuid"] == DATA_TIMBRADO["uuid"]
        assert body["cfdi"] == DATA_TIMBRADO["cfdi"]
        llamada_sw = mock_post.call_args_list[1]
        assert llamada_sw.args[0] == "https://sw.test/cfdi33/stamp/v4"
        assert llamada_sw.kwargs["headers"] == {"Authorization": "Bearer tok"}
        assert llamada_sw.kwargs["files"]["xml"][1] == cfdi().encode("utf-8")
        h.certificates_collection.find_one.assert_called_once_with({"rfc": RFC_EMISOR})
        registro = h.bitacora_collection.insert_one.call_args.args[0]
        assert registro["status"] == "exito"
        assert registro["rfcEmisor"] == RFC_EMISOR
        assert registro["rfc"] == "XAXX010101000"

    @patch("invoice_cdk.lambdas.timbrado_xml_handler.requests.post")
    def test_body_en_base64(self, mock_post, h):
        mock_post.side_effect = [respuesta_token(), respuesta_sw({"data": DATA_TIMBRADO, "status": "success"})]

        r = h.handler(evento(cfdi(), base64_encoded=True), {})

        assert r["statusCode"] == 200
        assert mock_post.call_args_list[1].kwargs["files"]["xml"][1] == cfdi().encode("utf-8")


class TestValidaciones:
    @pytest.mark.parametrize("xml, fragmento", [
        ("", "debe contener el XML"),
        ("esto no es xml", "no es válido"),
        (cfdi(version="3.3"), "CFDI 4.0"),
        (cfdi(ns="http://www.sat.gob.mx/cfd/3"), "CFDI 4.0"),
        (cfdi(sello=""), "sellado"),
        (cfdi(cert=""), "sellado"),
        (cfdi(rfc_emisor=""), "RFC del emisor"),
    ])
    @patch("invoice_cdk.lambdas.timbrado_xml_handler.requests.post")
    def test_rechaza_sin_llamar_a_sw(self, mock_post, h, xml, fragmento):
        r = h.handler(evento(xml), {})
        assert r["statusCode"] == 400
        assert fragmento in json.loads(r["body"])["message"]
        mock_post.assert_not_called()

    @patch("invoice_cdk.lambdas.timbrado_xml_handler.requests.post")
    def test_emisor_no_registrado(self, mock_post, h):
        h.certificates_collection.find_one.return_value = None
        r = h.handler(evento(cfdi()), {})
        assert r["statusCode"] == 404
        mock_post.assert_not_called()
        assert h.bitacora_collection.insert_one.call_args.args[0]["status"] == "error"

    def test_metodo_no_permitido(self, h):
        assert h.handler({"httpMethod": "GET"}, {})["statusCode"] == 405


class TestErroresSW:
    @patch("invoice_cdk.lambdas.timbrado_xml_handler.requests.post")
    def test_sat_rechaza_comprobante(self, mock_post, h):
        mock_post.side_effect = [respuesta_token(), respuesta_sw({
            "message": "CFDI40108 - El TipoDeComprobante no es válido.",
            "messageDetail": "detalle del SAT",
            "data": None,
            "status": "error",
        })]

        r = h.handler(evento(cfdi()), {})

        assert r["statusCode"] == 400
        body = json.loads(r["body"])
        assert body["status"] == "error"
        assert body["message"] == "CFDI40108 - El TipoDeComprobante no es válido."
        assert body["detalle"] == "detalle del SAT"

    @patch("invoice_cdk.lambdas.timbrado_xml_handler.requests.post")
    def test_falla_autenticacion_sw(self, mock_post, h):
        mock_post.side_effect = [respuesta_sw({"message": "AU2000", "data": None, "status": "error"})]
        r = h.handler(evento(cfdi()), {})
        assert r["statusCode"] == 502

    @patch("invoice_cdk.lambdas.timbrado_xml_handler.requests.post")
    def test_sw_no_responde(self, mock_post, h):
        import requests
        mock_post.side_effect = requests.ConnectionError("timeout")
        r = h.handler(evento(cfdi()), {})
        assert r["statusCode"] == 502
