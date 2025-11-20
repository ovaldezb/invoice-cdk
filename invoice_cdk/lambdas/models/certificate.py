from pydantic import BaseModel
from typing import List, Optional
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

class CertificadoUpdate(Certificado):
    rfc: Optional[str] = None
    nombre: Optional[str] = None
    no_certificado: Optional[str] = None
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    sucursales: Optional[List[Sucursal]] = None
    usuario: Optional[str] = None

class Config:
    exclude_none = True