from datetime import datetime, timezone

def consulta_facturas_emitidas_by_certificado(id_certificado, desde: str, hasta: str, facturas_emitidas_collection=None):
    desde_dt = datetime.strptime(desde + 'T00:00:00', "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    hasta_dt = datetime.strptime(hasta + 'T23:59:59', "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    facturas_emitidas = facturas_emitidas_collection.find({
        "idCertificado": id_certificado,
        "fechaTimbrado": {"$gte": desde_dt, "$lte": hasta_dt}
    })
    return list(facturas_emitidas)

