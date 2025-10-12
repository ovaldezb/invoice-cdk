from datetime import datetime
from pydantic import BaseModel

class FacturaEmitida(BaseModel):
    cadenaOriginalSAT: str
    cfdi: str
    fechaTimbrado: datetime
    noCertificadoCFDI: str
    noCertificadoSAT: str
    qrCode: str
    selloCFDI: str
    selloSAT: str
    uuid: str
    sucursal: str
    idCertificado: str
    ticket: str
    estatus: str