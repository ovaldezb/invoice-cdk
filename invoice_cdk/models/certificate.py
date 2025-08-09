from pydantic import BaseModel
from typing import List
from datetime import date

class Certificado(BaseModel):
    nombre: str
    rfc: str
    no_certificado: str
    desde: date
    hasta: date
    sucursales: List[str]
    usuario: str
