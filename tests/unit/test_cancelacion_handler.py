"""
Unit tests for cancelacion_handler (POST /cancelacion).
Usan mocks: no requieren base de datos ni acceso a SW.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

UUID = "5AB1CCC8-2CA2-471F-88FE-BBFA84153459"
UUID_SUST = "A29C3936-89A6-4BFD-AC82-B41DA2C51AA4"
RFC_EMISOR = "EKU9003173C9"
RFC_RECEPTOR = "URE180429TM6"

CFDI_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0">'
    f'<cfdi:Emisor Rfc="{RFC_EMISOR}" Nombre="EMISOR" RegimenFiscal="601"/>'
    f'<cfdi:Receptor Rfc="{RFC_RECEPTOR}" Nombre="RECEPTOR" UsoCFDI="G03"/>'
    '</cfdi:Comprobante>'
)


@pytest.fixture
def h():
    import invoice_cdk.lambdas.cancelacion_handler as handler_module
    handler_module.facturas_emitidas_collection = MagicMock()
    handler_module.certificates_collection = MagicMock()
    handler_module.bitacora_collection = MagicMock()
    handler_module.SW_URL = "https://sw.test"
    return handler_module


def evento(body):
    return {"httpMethod": "POST", "body": json.dumps(body)}


def body_base(**extra):
    body = {"uuid": UUID, "rfcReceptor": RFC_RECEPTOR, "ticket": "T-100", "motivo": "02"}
    body.update(extra)
    return body


def factura_bd(**extra):
    factura = {"uuid": UUID, "ticket": "T-100", "estatus": "Vigente", "cfdi": CFDI_XML}
    factura.update(extra)
    return factura


def respuesta_sw(code, message="Solicitud de cancelación exitosa."):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": {"acuse": "<Acuse/>", "uuid": {UUID: {"code": code, "message": message, "description": "desc"}}},
        "status": "success",
    }
    return resp


def respuesta_token():
    resp = MagicMock()
    resp.json.return_value = {"data": {"token": "tok"}, "status": "success"}
    return resp


class TestValidaciones:
    def test_motivo_invalido(self, h):
        r = h.handler(evento(body_base(motivo="05")), {})
        assert r["statusCode"] == 400
        assert any("motivo" in d for d in json.loads(r["body"])["detalle"])

    def test_uuid_invalido(self, h):
        r = h.handler(evento(body_base(uuid="no-es-uuid")), {})
        assert r["statusCode"] == 400

    def test_motivo_01_sin_folio_sustitucion(self, h):
        r = h.handler(evento(body_base(motivo="01")), {})
        assert r["statusCode"] == 400
        assert any("folioSustitucion" in d for d in json.loads(r["body"])["detalle"])

    def test_motivo_01_folio_igual_al_uuid(self, h):
        r = h.handler(evento(body_base(motivo="01", folioSustitucion=UUID)), {})
        assert r["statusCode"] == 400

    def test_folio_sustitucion_con_motivo_distinto_de_01(self, h):
        r = h.handler(evento(body_base(motivo="02", folioSustitucion=UUID_SUST)), {})
        assert r["statusCode"] == 400

    def test_json_malformado(self, h):
        r = h.handler({"httpMethod": "POST", "body": "{no json"}, {})
        assert r["statusCode"] == 400

    def test_metodo_no_permitido(self, h):
        r = h.handler({"httpMethod": "GET"}, {})
        assert r["statusCode"] == 405


class TestFacturaDeEsteSistema:
    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_cancelacion_exitosa_queda_en_proceso(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd()
        mock_post.side_effect = [respuesta_token(), respuesta_sw("201")]

        r = h.handler(evento(body_base()), {})

        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["estatus"] == "En proceso de cancelación"
        assert body["emitidaPorEsteSistema"] is True
        assert mock_post.call_args_list[1].args[0] == f"https://sw.test/cfdi33/cancel/{RFC_EMISOR}/{UUID}/02/v2"
        filtro, cambios = h.facturas_emitidas_collection.update_one.call_args.args
        assert filtro == {"uuid": UUID}
        assert cambios["$set"]["estatus"] == "En proceso de cancelación"
        assert cambios["$set"]["cancelacion"]["acuse"] == "<Acuse/>"
        assert h.bitacora_collection.insert_one.call_args.args[0]["status"] == "exito"

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_previamente_cancelada_se_marca_cancelada(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd()
        mock_post.side_effect = [respuesta_token(), respuesta_sw("202", "Folio Fiscal Previamente Cancelado.")]

        r = h.handler(evento(body_base()), {})

        assert r["statusCode"] == 200
        assert json.loads(r["body"])["estatus"] == "Cancelada"

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_motivo_01_agrega_folio_sustitucion_a_la_url(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd()
        mock_post.side_effect = [respuesta_token(), respuesta_sw("201")]

        r = h.handler(evento(body_base(motivo="01", folioSustitucion=UUID_SUST.lower())), {})

        assert r["statusCode"] == 200
        assert mock_post.call_args_list[1].args[0] == (
            f"https://sw.test/cfdi33/cancel/{RFC_EMISOR}/{UUID}/01/{UUID_SUST}/v2"
        )

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_ya_cancelada_no_llama_a_sw(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd(estatus="Cancelada")
        r = h.handler(evento(body_base()), {})
        assert r["statusCode"] == 409
        mock_post.assert_not_called()

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_en_proceso_de_cancelacion_no_llama_a_sw(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd(estatus="En proceso de cancelación")
        r = h.handler(evento(body_base()), {})
        assert r["statusCode"] == 409
        assert json.loads(r["body"])["message"] == "La factura ya tiene una solicitud de cancelación en proceso"
        mock_post.assert_not_called()
        h.facturas_emitidas_collection.update_one.assert_not_called()
        assert h.bitacora_collection.insert_one.call_args.args[0]["status"] == "error"

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_ticket_no_coincide(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd(ticket="OTRO")
        r = h.handler(evento(body_base()), {})
        assert r["statusCode"] == 422
        mock_post.assert_not_called()

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_sin_ticket(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd()
        body = body_base()
        del body["ticket"]
        r = h.handler(evento(body), {})
        assert r["statusCode"] == 400
        mock_post.assert_not_called()

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_rfc_receptor_no_coincide(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd()
        r = h.handler(evento(body_base(rfcReceptor="XAXX010101000")), {})
        assert r["statusCode"] == 422
        mock_post.assert_not_called()

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_sat_rechaza_con_otro_codigo(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd()
        mock_post.side_effect = [respuesta_token(), respuesta_sw("205", "Folio Fiscal No Existente.")]

        r = h.handler(evento(body_base()), {})

        assert r["statusCode"] == 422
        assert json.loads(r["body"])["message"] == "Folio Fiscal No Existente."
        h.facturas_emitidas_collection.update_one.assert_not_called()

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_sw_responde_error(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = factura_bd()
        error = MagicMock()
        error.status_code = 400
        error.json.return_value = {
            "message": "CACFDI33 - Problemas con el xml.",
            "messageDetail": "CA305 - Certificado Inválido.",
            "data": None,
            "status": "error",
        }
        mock_post.side_effect = [respuesta_token(), error]

        r = h.handler(evento(body_base()), {})

        assert r["statusCode"] == 502
        assert json.loads(r["body"])["detalle"] == "CA305 - Certificado Inválido."
        h.facturas_emitidas_collection.update_one.assert_not_called()
        assert h.bitacora_collection.insert_one.call_args.args[0]["status"] == "error"


class TestFacturaDeOtroSistema:
    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_cancelacion_exitosa_con_certificado_registrado(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = None
        h.certificates_collection.find_one.return_value = {"rfc": RFC_EMISOR}
        mock_post.side_effect = [respuesta_token(), respuesta_sw("201")]

        body = body_base(rfcEmisor=RFC_EMISOR.lower())
        del body["ticket"]
        r = h.handler(evento(body), {})

        assert r["statusCode"] == 200
        assert json.loads(r["body"])["emitidaPorEsteSistema"] is False
        h.certificates_collection.find_one.assert_called_once_with({"rfc": RFC_EMISOR})
        h.facturas_emitidas_collection.update_one.assert_not_called()

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_sin_rfc_emisor(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = None
        r = h.handler(evento(body_base()), {})
        assert r["statusCode"] == 400
        mock_post.assert_not_called()

    @patch("invoice_cdk.lambdas.cancelacion_handler.requests.post")
    def test_emisor_sin_certificado_registrado(self, mock_post, h):
        h.facturas_emitidas_collection.find_one.return_value = None
        h.certificates_collection.find_one.return_value = None
        r = h.handler(evento(body_base(rfcEmisor=RFC_EMISOR)), {})
        assert r["statusCode"] == 404
        mock_post.assert_not_called()
