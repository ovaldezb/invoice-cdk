"""
Unit tests de fecha_cfdi: la Fecha del CFDI se asigna con la hora del servidor.
"""
import json
import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from invoice_cdk.lambdas import fecha_cfdi

FORMATO_CFDI = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def test_fecha_en_hora_cdmx_con_margen():
    ahora = datetime(2026, 11, 17, 18, 30, 0, tzinfo=timezone.utc)  # 12:30 en CDMX
    assert fecha_cfdi.fecha_emision_cfdi(ahora) == "2026-11-17T12:25:00"


def test_fecha_cambia_de_dia_al_convertir_a_cdmx():
    ahora = datetime(2026, 11, 18, 3, 0, 0, tzinfo=timezone.utc)  # 21:00 del día anterior en CDMX
    assert fecha_cfdi.fecha_emision_cfdi(ahora) == "2026-11-17T20:55:00"


def test_asigna_fecha_sobrescribe_la_del_cliente():
    timbrado = {"Fecha": "2026-11-01T10:00:00", "Serie": "A"}
    with patch.object(fecha_cfdi, "fecha_emision_cfdi", return_value="2026-11-17T12:25:00"):
        resultado = fecha_cfdi.asigna_fecha_emision(timbrado)
    assert resultado is timbrado
    assert timbrado["Fecha"] == "2026-11-17T12:25:00"
    assert timbrado["Serie"] == "A"


def test_asigna_fecha_sin_fecha_del_cliente():
    timbrado = {}
    fecha_cfdi.asigna_fecha_emision(timbrado)
    assert FORMATO_CFDI.match(timbrado["Fecha"])


@patch("invoice_cdk.lambdas.timbrado_service_handler.requests.post")
def test_timbrado_service_envia_fecha_del_servidor(mock_post):
    import invoice_cdk.lambdas.timbrado_service_handler as handler_module

    auth = MagicMock()
    auth.json.return_value = {"status": "success", "data": {"token": "tok"}}
    timbre = MagicMock()
    timbre.json.return_value = {"status": "success", "data": {}}
    mock_post.side_effect = [auth, timbre]

    event = {"httpMethod": "POST", "body": json.dumps({"timbrado": {"Fecha": "2020-01-01T00:00:00", "Serie": "F"}})}
    with patch("invoice_cdk.lambdas.timbrado_service_handler.asigna_fecha_emision",
               side_effect=lambda t: t.update(Fecha="2026-11-17T12:25:00") or t):
        r = handler_module.handler(event, {})

    assert r["statusCode"] == 200
    enviado = json.loads(mock_post.call_args_list[1].kwargs["data"])
    assert enviado["Fecha"] == "2026-11-17T12:25:00"
