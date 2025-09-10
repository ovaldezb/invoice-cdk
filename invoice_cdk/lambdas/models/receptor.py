from pydantic import BaseModel
class Receptor(BaseModel):
    _id: str
    Nombre: str
    DomicilioFiscalReceptor: str
    email: str
    Rfc: str
    RegimenFiscalReceptor: str
    UsoCFDI: str
