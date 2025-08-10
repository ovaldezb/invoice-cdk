from pydantic import BaseModel

class Usuario(BaseModel):
    id: str
    nombre: str
    razon_social: str
    email: str
    rfc: str
    telefono: str
    