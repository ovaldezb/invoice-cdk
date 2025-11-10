from email.utils import formataddr, make_msgid
import os
import smtplib
import base64
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders


SMTP_HOST=os.getenv('SMTP_HOST')
SMTP_PORT=os.getenv('SMTP_PORT')
SMTP_USER=os.getenv('SMTP_USER')
SMTP_PASSWORD=os.getenv('SMTP_PASSWORD')
FROM=os.getenv('SMTP_FROM') 
SMTP_BCC=os.getenv('SMTP_BCC')
REPLY_TO=os.getenv('SMTP_REPLY_TO')

class EmailSender:
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_pass = SMTP_PASSWORD
        self.use_tls = True

    def send_invoice(self, recipient_email: str, pdf_base64: str, cfdi_xml: str,
                     pdf_filename: str, xml_filename: str,
                     subject: str, body_text: str) -> bool:
        # Construir mensaje MIME (igual que antes)
        msg = MIMEMultipart('related')

        msg['From'] = formataddr((FROM, REPLY_TO))
        msg['To'] = ', '.join([recipient_email])
        msg['Reply-To'] = REPLY_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain'))
        # Headers anti-spam críticos
        msg['Message-ID'] = make_msgid(domain="farzin.com.mx")
        msg['X-Mailer'] = 'Facturacion Farzin v1.0'
        msg['X-Priority'] = '3'  # Normal priority (1=High, 3=Normal, 5=Low)
        msg['Importance'] = 'normal'
        # Headers de lista de correo legítimo
        msg['List-Unsubscribe'] = f'<mailto:{REPLY_TO}?subject=Unsubscribe>'
        msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
        msg['List-ID'] = 'CE Integration Station Weekly Quiz <quiz.ce-integration-station.com>'
        # Headers de autenticación y legitimidad
        msg['Organization'] = 'Facturacion Farzin'
        msg['X-Auto-Response-Suppress'] = 'OOF'  # Evita respuestas automáticas
        TO=[recipient_email]
        BCC=[SMTP_BCC]

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
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            server.set_debuglevel(1)  # para depuración
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(FROM, TO + BCC, msg.as_string())
            server.quit()
            print("Email sent via SES")
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            traceback.print_exc()
            return False
   