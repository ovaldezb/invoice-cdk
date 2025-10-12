from models.factura_emitida import FacturaEmitida

def guarda_factura_emitida(factura_emitida: FacturaEmitida, facturas_emitidas_collection):
    facturas_emitidas_collection.insert_one(factura_emitida.dict())

def get_factura_by_uuid(uuid: str, facturas_emitidas_collection):
    return facturas_emitidas_collection.find_one({"uuid": uuid})

def cancela_factura_status(uuid: str,  facturas_emitidas_collection):
    facturas_emitidas_collection.update_one({"uuid": uuid}, {"$set": {"estatus": "Cancelada"}})