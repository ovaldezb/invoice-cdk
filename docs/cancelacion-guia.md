# Guía de integración: API de cancelación de facturas

Esta guía explica cómo solicitar la cancelación de una factura electrónica (CFDI 4.0) desde su sistema. La especificación técnica completa está en el archivo `cancelacion-openapi.yaml`, que puede abrir en [editor.swagger.io](https://editor.swagger.io) o importar en Postman.

## 1. Datos de conexión

| Ambiente | URL |
|---|---|
| Desarrollo (pruebas) | `https://v6z1l22kw7.execute-api.us-west-1.amazonaws.com/prod/cancelacion` |
| Producción | Se proporcionará al liberar |

- **Método:** `POST`
- **Formato:** JSON (`Content-Type: application/json`)
- **Autenticación:** header `x-api-key` con la llave que le entregamos por un canal seguro. Cada ambiente tiene su propia llave.
- **Límites:** 5 peticiones por segundo (ráfagas de hasta 10) y 1,000 peticiones por día.

> La API Key es confidencial. Úsela solo desde su servidor; nunca la incluya en páginas web, aplicaciones móviles ni repositorios de código. Si cree que se expuso, avísenos para reemplazarla.

## 2. Petición

```http
POST /cancelacion
x-api-key: <su API Key>
Content-Type: application/json

{
  "uuid": "5AB1CCC8-2CA2-471F-88FE-BBFA84153459",
  "rfcReceptor": "URE180429TM6",
  "ticket": "100245",
  "motivo": "02"
}
```

### Campos

| Campo | Obligatorio | Descripción |
|---|---|---|
| `uuid` | Siempre | Folio fiscal de la factura a cancelar |
| `rfcReceptor` | Siempre | RFC del cliente al que se emitió la factura |
| `motivo` | Siempre | Motivo de cancelación del SAT: `01`, `02`, `03` o `04` (ver sección 3) |
| `ticket` | Si la factura la emitió esta plataforma | Número de ticket de la venta |
| `rfcEmisor` | Si la factura la emitió **otro** sistema | RFC de la tienda que emitió la factura |
| `folioSustitucion` | Solo con motivo `01` | UUID de la factura nueva que sustituye a la cancelada |

Usted no necesita saber qué sistema emitió la factura: la plataforma busca el UUID y aplica la validación que corresponde. Si tiene el ticket, envíelo; si la factura es de otro sistema, envíe además `rfcEmisor`.

**Facturas emitidas por otro sistema:** también se pueden cancelar, siempre que la tienda emisora tenga su certificado de sello digital (CSD) registrado en esta plataforma. Si no lo tiene, la respuesta será `404`.

## 3. Motivos de cancelación (catálogo del SAT)

| Clave | Motivo | Cuándo usarlo |
|---|---|---|
| `01` | Comprobante emitido con errores con relación | La factura tiene un error y **ya se emitió una nueva** que la reemplaza. Envíe el UUID de la nueva en `folioSustitucion`. |
| `02` | Comprobante emitido con errores sin relación | La factura tiene un error y no se va a reemplazar con otra relacionada. |
| `03` | No se llevó a cabo la operación | La venta no se concretó (por ejemplo, una devolución total o una operación que se canceló). |
| `04` | Operación nominativa relacionada en una factura global | La venta se incluyó en una factura global (público en general) y después se facturó a nombre del cliente. |

Con motivo `01`, emita **primero** la factura que sustituye y después solicite la cancelación de la original.

## 4. Respuesta y estatus

Una respuesta `200` regresa:

```json
{
  "uuid": "5AB1CCC8-2CA2-471F-88FE-BBFA84153459",
  "estatus": "En proceso de cancelación",
  "codigoSat": "201",
  "mensaje": "Solicitud de cancelación exitosa.",
  "descripcion": "...",
  "emitidaPorEsteSistema": true,
  "acuse": "<?xml version=\"1.0\" ...>"
}
```

| `estatus` | Código SAT | Significado |
|---|---|---|
| `En proceso de cancelación` | 201 | El SAT recibió la solicitud. Si la factura no requiere aceptación del receptor, queda cancelada; si la requiere, se cancelará cuando el receptor acepte (ver sección 5). |
| `Cancelada` | 202 | La factura ya estaba cancelada ante el SAT. |

Guarde el `acuse`: es el comprobante del SAT de que se solicitó la cancelación.

Una factura que está en proceso de cancelación o ya cancelada **no puede volver a enviarse** (respuesta `409`).

## 5. Reglas del SAT que debe conocer

- **Aceptación del receptor:** normalmente el cliente que recibió la factura debe aceptar la cancelación desde el portal del SAT. Si no responde en 3 días hábiles, se considera aceptada. Si la rechaza, la factura sigue vigente.
- **No requieren aceptación**, entre otros casos:
    - facturas con total de hasta $1,000 MXN;
    - cancelaciones dentro de las 24 horas siguientes a la emisión;
    - facturas a público en general (RFC `XAXX010101000`).
- **Plazo:** una factura se puede cancelar a más tardar en la fecha en que vence la declaración anual del ejercicio en que se emitió.

## 6. Códigos de respuesta

| HTTP | Significado | Qué hacer |
|---|---|---|
| `200` | Solicitud recibida por el SAT, o factura ya cancelada | Revise `estatus` y guarde el `acuse` |
| `400` | Datos inválidos o incompletos | Revise `message` y `detalle`, corrija y reintente |
| `403` | API Key ausente o incorrecta | Verifique el header `x-api-key` |
| `404` | El emisor no tiene su CSD registrado en la plataforma | El emisor debe registrar su certificado antes de cancelar |
| `409` | La factura ya está cancelada o en proceso de cancelación | No reintente |
| `422` | El ticket o el RFC no corresponden a la factura, o el SAT rechazó la cancelación | Verifique los datos; `detalle.codigoSat` indica el motivo del SAT |
| `429` | Se excedió el límite de peticiones | Espere y reintente más tarde |
| `500` / `502` | Error interno o del proveedor de certificación | Reintente más tarde; si persiste, contáctenos con el UUID |

Los errores tienen este formato:

```json
{
  "message": "Solicitud inválida",
  "detalle": ["folioSustitucion es obligatorio con motivo 01 y debe tener formato de UUID"]
}
```

## 7. Ejemplos con curl

Factura emitida por esta plataforma:

```bash
curl -X POST "https://v6z1l22kw7.execute-api.us-west-1.amazonaws.com/prod/cancelacion" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "uuid": "5AB1CCC8-2CA2-471F-88FE-BBFA84153459",
        "rfcReceptor": "URE180429TM6",
        "ticket": "100245",
        "motivo": "02"
      }'
```

Sustitución de una factura (motivo 01):

```bash
curl -X POST "https://v6z1l22kw7.execute-api.us-west-1.amazonaws.com/prod/cancelacion" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "uuid": "5AB1CCC8-2CA2-471F-88FE-BBFA84153459",
        "rfcReceptor": "URE180429TM6",
        "ticket": "100245",
        "motivo": "01",
        "folioSustitucion": "A29C3936-89A6-4BFD-AC82-B41DA2C51AA4"
      }'
```

Factura emitida por otro sistema:

```bash
curl -X POST "https://v6z1l22kw7.execute-api.us-west-1.amazonaws.com/prod/cancelacion" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "uuid": "2F0499D1-693B-45F4-B3A6-5C06254933E3",
        "rfcEmisor": "EKU9003173C9",
        "rfcReceptor": "URE180429TM6",
        "motivo": "03"
      }'
```
