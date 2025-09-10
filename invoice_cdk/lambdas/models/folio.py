from pydantic import BaseModel

class Folio(BaseModel):
    _id: str
    sucursal: str
    noFolio: int