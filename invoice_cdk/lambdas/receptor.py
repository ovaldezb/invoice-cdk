from pydantic import BaseModel

class Receptor(BaseModel):
    Nombre: str
    DomicilioFiscalReceptor: str
    email: str
    Rfc: str
    RegimenFiscalReceptor: str
    UsoCFDI: str
