from pydantic import BaseModel
from typing import List
from datetime import datetime
from models.sucursal import Sucursal

class Certificado(BaseModel):
    nombre: str
    rfc: str
    no_certificado: str
    desde: datetime
    hasta: datetime
    sucursales: List[Sucursal]
    usuario: str
