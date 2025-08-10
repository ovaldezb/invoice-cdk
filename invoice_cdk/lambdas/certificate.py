from pydantic import BaseModel
from typing import List
from datetime import datetime

class Certificado(BaseModel):
    nombre: str
    rfc: str
    no_certificado: str
    desde: datetime
    hasta: datetime
    sucursales: List[str]
    usuario: str
