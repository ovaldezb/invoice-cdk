# -*- coding: utf-8 -*-
"""Pruebas de codificacion para receptores con enie y caracteres tipograficos.

Cubren, sin salir a la red, las tres piezas donde se perdia la codificacion:
  1. La declaracion encoding="UTF-8" del XML que se manda por correo y al ERP.
  2. La generacion del PDF con nombres fuera del rango latin-1.
  3. El armado del correo con asunto y cuerpo no ASCII.
"""
import os
import sys
import xml.dom.minidom
from pathlib import Path

import pytest

_LAMBDAS = Path(__file__).parent.parent.parent / 'invoice_cdk' / 'lambdas'
if str(_LAMBDAS) not in sys.path:
    sys.path.insert(0, str(_LAMBDAS))

from cfdi_pdf_fpdf_generator import sanea_latin1  # noqa: E402

# Nombre real de receptor con enie y acentos, mas los caracteres tipograficos
# que llegan del autollenado de la Constancia de Situacion Fiscal.
NOMBRE_CON_ENIE = 'MUÑOZ PEÑA JOSÉ ANTONIO'
NOMBRE_CON_TIPOGRAFICOS = 'COMERCIALIZADORA O’BRIEN – PEÑA S.A. DE C.V.'

CFDI_TIMBRADO = (
    '<?xml version="1.0"?>'
    '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" '
    'Serie="A" Folio="123" SubTotal="100.00" Total="116.00">'
    f'<cfdi:Receptor Rfc="MUPJ850315AB1" Nombre="{NOMBRE_CON_ENIE}" '
    'DomicilioFiscalReceptor="52756" UsoCFDI="G03"/>'
    '</cfdi:Comprobante>'
)


class TestDeclaracionEncodingXml:
    """El XML que sale hacia el correo y hacia el ERP debe declarar su codificacion."""

    def test_sin_encoding_el_xml_se_lee_mal_como_cp1252(self):
        """Reproduce el defecto original: sin declaracion, un lector local rompe la enie."""
        dom = xml.dom.minidom.parseString(CFDI_TIMBRADO)
        sin_declaracion = dom.toprettyxml(indent="  ")

        assert 'encoding' not in sin_declaracion.splitlines()[0]
        leido_como_local = sin_declaracion.encode('utf-8').decode('cp1252', 'replace')
        assert 'MUÑOZ' not in leido_como_local, 'la enie deberia salir corrupta sin declaracion'

    def test_con_encoding_declara_utf8_en_la_primera_linea(self):
        """Es exactamente lo que hace ahora genera_factura_handler."""
        dom = xml.dom.minidom.parseString(CFDI_TIMBRADO)
        pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

        assert pretty_xml.splitlines()[0] == '<?xml version="1.0" encoding="UTF-8"?>'
        assert NOMBRE_CON_ENIE in pretty_xml

    def test_agregar_encoding_no_altera_el_resto_del_documento(self):
        """El ERP recibe el mismo formato de siempre: solo cambia la primera linea."""
        dom = xml.dom.minidom.parseString(CFDI_TIMBRADO)
        sin_declaracion = dom.toprettyxml(indent="  ")
        con_declaracion = dom.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

        assert sin_declaracion.splitlines()[1:] == con_declaracion.splitlines()[1:]

    def test_el_xml_declarado_se_reparsea_y_conserva_la_enie(self):
        dom = xml.dom.minidom.parseString(CFDI_TIMBRADO)
        pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8")

        reparseado = xml.dom.minidom.parseString(pretty_xml)
        receptor = reparseado.getElementsByTagName('cfdi:Receptor')[0]
        assert receptor.getAttribute('Nombre') == NOMBRE_CON_ENIE


class TestSaneoLatin1:
    """fpdf 1.7.2 con fuentes core solo codifica latin-1."""

    def test_conserva_enie_y_acentos(self):
        """La enie SI cabe en latin-1: no debe degradarse a N."""
        resultado = sanea_latin1(NOMBRE_CON_ENIE)
        assert resultado == NOMBRE_CON_ENIE
        assert 'Ñ' in resultado
        assert 'É' in resultado

    def test_translitera_caracteres_fuera_de_latin1(self):
        resultado = sanea_latin1(NOMBRE_CON_TIPOGRAFICOS)
        resultado.encode('latin-1')  # no debe lanzar
        assert "O'BRIEN" in resultado
        assert 'PEÑA' in resultado, 'la enie sobrevive aunque haya que degradar otros caracteres'

    @pytest.mark.parametrize('entrada,esperado', [
        ('O’BRIEN', "O'BRIEN"),
        ('TAPETES – PREMIUM', 'TAPETES - PREMIUM'),
        ('COMILLAS “DOBLES”', 'COMILLAS "DOBLES"'),
        ('PUNTOS…', 'PUNTOS...'),
    ])
    def test_transliteraciones_conocidas(self, entrada, esperado):
        assert sanea_latin1(entrada) == esperado

    def test_caracter_irreducible_no_revienta(self):
        resultado = sanea_latin1('EMPRESA 株式会社')
        resultado.encode('latin-1')  # no debe lanzar
        assert resultado.startswith('EMPRESA ')

    @pytest.mark.parametrize('entrada', [None, 123, 45.6])
    def test_tolera_valores_no_string(self, entrada):
        assert isinstance(sanea_latin1(entrada), str)


class TestPdfConNombresProblematicos:
    """El PDF ya no debe reventar por el nombre del receptor."""

    @pytest.mark.parametrize('nombre', [NOMBRE_CON_ENIE, NOMBRE_CON_TIPOGRAFICOS])
    def test_fpdf_seguro_imprime_sin_reventar(self, nombre):
        from cfdi_pdf_fpdf_generator import _FPDFSeguro

        pdf = _FPDFSeguro()
        pdf.add_page()
        pdf.set_font('Arial', '', 8)
        pdf.cell(60, 4, nombre)
        pdf.multi_cell(60, 4, nombre)
        salida = pdf.output(dest='S').encode('latin-1')

        assert len(salida) > 0

    def test_fpdf_base_si_revienta_con_tipograficos(self):
        """Deja constancia del defecto original: sin el saneo, esto lanza."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 8)
        with pytest.raises(UnicodeEncodeError):
            pdf.cell(60, 4, NOMBRE_CON_TIPOGRAFICOS)
            pdf.output(dest='S')


class TestCorreoConEnie:
    """El asunto y el cuerpo deben viajar en UTF-8 declarado."""

    def test_asunto_y_cuerpo_no_ascii_se_codifican(self):
        from email.header import Header
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart('related')
        msg['Subject'] = Header(f'Factura del ticket {NOMBRE_CON_ENIE}', 'utf-8')
        msg.attach(MIMEText(f'Factura para {NOMBRE_CON_ENIE}', 'plain', 'utf-8'))

        crudo = msg.as_string()
        assert 'utf-8' in crudo.lower()

        from email import message_from_string
        recuperado = message_from_string(crudo)
        cuerpo = recuperado.get_payload(0).get_payload(decode=True).decode('utf-8')
        assert NOMBRE_CON_ENIE in cuerpo

    def test_adjunto_xml_conserva_la_enie(self):
        from email import encoders
        from email.mime.base import MIMEBase

        dom = xml.dom.minidom.parseString(CFDI_TIMBRADO)
        pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

        parte = MIMEBase('application', 'xml', charset='utf-8')
        parte.set_payload(pretty_xml.encode('utf-8'))
        encoders.encode_base64(parte)

        recuperado = parte.get_payload(decode=True).decode('utf-8')
        assert 'encoding="UTF-8"' in recuperado
        assert NOMBRE_CON_ENIE in recuperado
