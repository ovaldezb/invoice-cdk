from pydantic import BaseModel

class Usuario(BaseModel):
    id: str
    nombre: str
    razon_social: str
    email: str
    telefono: str
    