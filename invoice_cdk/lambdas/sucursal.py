from pydantic import BaseModel

class Sucursal(BaseModel):
    id_certificado: str
    codigo_sucursal: str
    direccion: str
    codigo_postal: str
    responsable: str
    telefono: str
