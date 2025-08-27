
def get_uso_cfdi(usocfdi_collection):
    return list(usocfdi_collection.find())

def get_regimen_fiscal(regimen_fiscal_collection):
    return list(regimen_fiscal_collection.find())

def get_forma_pago(forma_pago_collection):
    return list(forma_pago_collection.find())

def get_descripcion_by_clave(clave, medidas_collection):
    return medidas_collection.find_one({"clave": clave}).get("descripcion")
