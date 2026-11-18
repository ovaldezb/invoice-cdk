"""
Fecha de emisión del CFDI (atributo Fecha del Comprobante).

El SAT rechaza el timbrado (error 401) si la Fecha difiere más de 72 horas de la
hora del timbrado, o si es posterior a ella. Antes se tomaba del reloj del
navegador del usuario, que puede estar desfasado; por eso el backend la asigna
con la hora del servidor justo antes de enviar el CFDI al PAC.
"""
from datetime import datetime, timedelta, timezone

# Hora del centro de México. Desde octubre de 2022 no aplica horario de verano.
ZONA_CDMX = timezone(timedelta(hours=-6))

# Margen hacia atrás para absorber desfases de reloj con el SAT y evitar el
# rechazo por fecha futura.
MARGEN_MINUTOS = 5


def fecha_emision_cfdi(ahora=None):
    """Regresa la fecha en formato CFDI (AAAA-MM-DDThh:mm:ss) en hora del centro de México."""
    ahora = ahora or datetime.now(timezone.utc)
    fecha = ahora.astimezone(ZONA_CDMX) - timedelta(minutes=MARGEN_MINUTOS)
    return fecha.strftime("%Y-%m-%dT%H:%M:%S")


def asigna_fecha_emision(timbrado):
    """Sobrescribe timbrado['Fecha'] con la hora del servidor y registra el cambio en el log."""
    fecha_recibida = timbrado.get("Fecha")
    timbrado["Fecha"] = fecha_emision_cfdi()
    print(f"Fecha CFDI recibida del cliente: {fecha_recibida} -> asignada por el servidor: {timbrado['Fecha']}")
    return timbrado
