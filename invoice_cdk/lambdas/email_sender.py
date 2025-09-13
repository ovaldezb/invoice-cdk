import os
import smtplib
import base64
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import boto3

SMTP_HOST=os.getenv('SMTP_HOST')
SMTP_PORT=os.getenv('SMTP_PORT')
SMTP_USER=os.getenv('SMTP_USER')
SMTP_PASSWORD=os.getenv('SMTP_PASSWORD')

class EmailSender:
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_pass = SMTP_PASSWORD
        self.use_tls = True

    def send_invoice(self, recipient_email: str, pdf_base64: str, cfdi_xml: str,
                     pdf_filename: str = 'factura.pdf', xml_filename: str = 'cfdi.xml',
                     subject: str = 'Factura', body_text: str = 'Adjunto factura en PDF y XML') -> bool:
        # Construir mensaje MIME (igual que antes)
        msg = MIMEMultipart()
        from_addr = os.getenv('SMTP_FROM') or self.smtp_user or 'no-reply@example.com'
        msg['From'] = from_addr
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain'))

        if pdf_base64:
            pdf_bytes = base64.b64decode(pdf_base64)
            part_pdf = MIMEBase('application', 'pdf')
            part_pdf.set_payload(pdf_bytes)
            encoders.encode_base64(part_pdf)
            part_pdf.add_header('Content-Disposition', f'attachment; filename="{pdf_filename}"')
            msg.attach(part_pdf)

        if cfdi_xml:
            xml_bytes = cfdi_xml.encode('utf-8') if isinstance(cfdi_xml, str) else cfdi_xml
            part_xml = MIMEBase('application', 'xml')
            part_xml.set_payload(xml_bytes)
            encoders.encode_base64(part_xml)
            part_xml.add_header('Content-Disposition', f'attachment; filename="{xml_filename}"')
            msg.attach(part_xml)

        try:
            # Usar SMTP (SES SMTP endpoint) con las credenciales SMTP_USER / SMTP_PASSWORD
            server = smtplib.SMTP(self.smtp_host, int(self.smtp_port), timeout=30)
            server.set_debuglevel(1)  # para depuración
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(from_addr, [recipient_email], msg.as_string())
            server.quit()
            print("Email sent via SES")
            return True
        except Exception as e:
            traceback.print_exc()
            return False
   