
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

def generar_pdf_factura(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, height - 40, "INDUSTRIAS CON CLASE SA DE CV")
    c.setFont("Helvetica", 8)
    c.drawString(30, height - 60, f"RFC emisor: {data['Emisor']['Rfc']}")
    c.drawString(30, height - 70, f"Nombre emisor: {data['Emisor']['Nombre']}")
    c.drawString(30, height - 80, f"Régimen Fiscal: {data['Emisor']['RegimenFiscal']}")

    # Receptor
    c.drawString(30, height - 100, f"Nombre receptor: {data['Receptor']['Nombre']}")
    c.drawString(30, height - 110, f"RFC receptor: {data['Receptor']['Rfc']}")
    c.drawString(30, height - 120, f"Uso CFDI: {data['Receptor']['UsoCFDI']}")

    # Datos generales
    c.drawString(400, height - 60, f"Serie: {data['Serie']}")
    c.drawString(400, height - 70, f"Folio: {data['Folio']}")
    c.drawString(400, height - 80, f"Fecha: {data['Fecha']}")
    c.drawString(400, height - 90, f"Forma de pago: {data['FormaPago']}")
    c.drawString(400, height - 100, f"Método de pago: {data['MetodoPago']}")
    c.drawString(400, height - 110, f"Condiciones de pago: {data['CondicionesDePago']}")

    # Tabla de conceptos
    c.setFont("Helvetica-Bold", 9)
    c.drawString(30, height - 150, "Conceptos")
    c.setFont("Helvetica", 8)
    y = height - 165
    c.drawString(30, y, "ClaveProdServ")
    c.drawString(100, y, "Cantidad")
    c.drawString(140, y, "Unidad")
    c.drawString(180, y, "Descripción")
    c.drawString(350, y, "Valor Unitario")
    c.drawString(420, y, "Importe")
    y -= 12
    for concepto in data["Conceptos"]:
        c.drawString(30, y, str(concepto["ClaveProdServ"]))
        c.drawString(100, y, str(concepto["Cantidad"]))
        c.drawString(140, y, concepto["Unidad"])
        c.drawString(180, y, concepto["Descripcion"])
        c.drawString(350, y, f"${concepto['ValorUnitario']:.2f}")
        c.drawString(420, y, f"${concepto['Importe']:.2f}")
        y -= 12

    # Totales
    y -= 20
    c.setFont("Helvetica-Bold", 9)
    c.drawString(350, y, "Subtotal:")
    c.drawString(420, y, f"${data['SubTotal']:.2f}")
    y -= 12
    c.drawString(350, y, "Descuento:")
    c.drawString(420, y, f"${data['Descuento']:.2f}")
    y -= 12
    c.drawString(350, y, "IVA 16%:")
    iva = data.get("Impuestos", {}).get("TotalImpuestosTrasladados", 0)
    c.drawString(420, y, f"${iva:.2f}")
    y -= 12
    c.drawString(350, y, "TOTAL:")
    c.drawString(420, y, f"${data['Total']:.2f}")

    # Pie de página
    c.setFont("Helvetica", 7)
    c.drawString(30, 30, "Este documento es una representación impresa de un CFDI")

    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
