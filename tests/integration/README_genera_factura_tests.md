# Tests de Integración - genera_factura_handler

## Resumen

Este documento describe los tests de integración implementados para el handler `genera_factura_handler.py`.

## Tests Implementados

### 1. Test Happy Path ✅
**Nombre:** `test_genera_factura_success`  
**Descripción:** Verifica que una factura se genere exitosamente con todos los datos válidos.

**Validaciones:**
- ✅ Respuesta HTTP 200 OK
- ✅ UUID generado correctamente
- ✅ Folio asignado e incrementado
- ✅ Factura guardada en `facturas_emitidas`
- ✅ Ticket registrado en `ticket_timbrado`
- ✅ Entrada de éxito en `bitacora`
- ✅ Serie-folio creado correctamente

---

### 2. Test Invalid CP (Código Postal) ❌→✅
**Nombre:** `test_genera_factura_invalid_cp_error`  
**Descripción:** Verifica el manejo de error cuando el código postal del receptor es inválido.

**Validaciones:**
- ✅ Respuesta HTTP 400 Bad Request
- ✅ Mensaje de error contiene "CFDI40147"
- ✅ Folio NO incrementado (rollback correcto)
- ✅ Ticket NO registrado (prevención de duplicados)
- ✅ Entrada de error en `bitacora` con detalles
- ✅ Sin datos en `facturas_emitidas`

---

### 3. Test Duplicate Ticket 🚫
**Nombre:** `test_genera_factura_duplicate_ticket_error`  
**Descripción:** Verifica que no se permita timbrar el mismo ticket dos veces.

**Escenario:**
1. Primera factura: éxito con ticket `TLE26262-XXXXXXX`
2. Segunda factura: intento con mismo ticket → ERROR

**Validaciones:**
- ✅ Primera factura: HTTP 200 OK
- ✅ Segunda factura: HTTP 400 Bad Request
- ✅ Error contiene "Ticket ya ha sido timbrado"
- ✅ Folio incrementado solo UNA vez
- ✅ Solo UNA factura en `facturas_emitidas`
- ✅ Índice único en `ticket_timbrado` funcionando

---

### 4. Test Folio Rollback 🔄
**Nombre:** `test_genera_factura_folio_rollback_on_error`  
**Descripción:** Verifica que cuando falla el timbrado, el folio se decrementa para ser reutilizado en el siguiente intento exitoso.

**Escenario:**
1. Folio inicial: `1015`
2. Primera factura con CP inválido → ERROR → Folio regresa a `1015`
3. Segunda factura con CP válido → ÉXITO → Usa folio `1015` → Incrementa a `1016`

**Validaciones:**
- ✅ Folio inicial capturado correctamente
- ✅ Primer intento falla (CP inválido)
- ✅ Folio decrementado (rollback) al valor inicial
- ✅ Segundo intento exitoso con folio reutilizado
- ✅ Folio incrementado después del éxito
- ✅ Factura guardada con folio correcto en CFDI XML
- ✅ Entradas correctas en bitácora (error + éxito)

**Importancia:** Este test es crítico para cumplir con SAT. Los folios deben ser consecutivos sin huecos.

---

### 5. Test Similar Tickets 🎫🎫
**Nombre:** `test_genera_factura_similar_tickets_success`  
**Descripción:** Verifica que dos tickets con números similares (mismo sufijo, diferente prefijo) se puedan timbrar sin conflictos.

**Ejemplo de Tickets:**
- `TLE26198-1528825`
- `TLE26210-1528825`

**Validaciones:**
- ✅ Ambos tickets se timbran exitosamente
- ✅ UUIDs diferentes generados
- ✅ Folios consecutivos asignados (1015, 1016)
- ✅ Ambos tickets en `ticket_timbrado`
- ✅ Ambas facturas en `facturas_emitidas`
- ✅ Entradas correctas en `bitacora`
- ✅ Serie-folio creado para cada uno
- ✅ Sin conflictos detectados

---

## Ejecución de Tests

### Ejecutar solo tests de genera_factura_handler:
```bash
.venv/bin/python -m pytest tests/integration/test_genera_factura_handler_integration.py -v
```

### Ejecutar un test específico:
```bash
.venv/bin/python -m pytest tests/integration/test_genera_factura_handler_integration.py::TestGeneraFacturaHandlerIntegrationErrors::test_genera_factura_folio_rollback_on_error -v -s
```

### Ejecutar todos los tests de handlers con coverage:
```bash
./run_all_handler_tests.sh integration
```

---

## Configuración Requerida

### Variables de Entorno (.env_test):
```bash
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=tufan_dev
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
SW_URL=https://services.test.sw.com.mx
SW_USER=xxx
SW_PASSWORD=xxx
```

### Colecciones MongoDB Requeridas:
- `facturas_emitidas`
- `folios`
- `ticket_timbrado` (con índice único en campo `ticket`)
- `serie_folio`
- `bitacora`
- `regimenfiscal`

---

## Notas Técnicas

### Índice Único en ticket_timbrado
```python
test_collections['ticket_timbrado'].create_index("ticket", unique=True)
```
Este índice es **crítico** para prevenir facturas duplicadas.

### Extracción de Folio del CFDI
El folio no se guarda como campo separado en MongoDB. Se extrae del XML CFDI:
```python
import re
folio_match = re.search(r'Folio="(\d+)"', factura['cfdi'])
folio = folio_match.group(1) if folio_match else None
```

### Formato de Tickets
Los tickets siguen el formato: `TLE26262-XXXXXXX` donde X es un número aleatorio de 7 dígitos.

En la base de datos `ticket_timbrado` se guardan **sin guiones**: `TLE262625484344`

---

## Cobertura de Código

Los tests cubren:
- ✅ Flujo exitoso de facturación (happy path)
- ✅ Manejo de errores de validación SAT
- ✅ Prevención de duplicados
- ✅ Rollback de folios
- ✅ Casos edge (tickets similares)
- ✅ Integración con SW Sapiens (sandbox)
- ✅ Integración con MongoDB
- ✅ Envío de emails (SES)

---

## Próximos Tests a Implementar

- [ ] Test de cancelación de factura
- [ ] Test de timbre con diferentes formas de pago
- [ ] Test de factura con múltiples conceptos
- [ ] Test de factura con descuentos
- [ ] Test de factura con diferentes regímenes fiscales
- [ ] Test de timeout en servicio de timbrado
- [ ] Test de límite de timbres disponibles

---

## Changelog

### 2025-11-25
- ✅ Implementados 5 tests de integración completos
- ✅ Integrados en `run_all_handler_tests.sh`
- ✅ Documentación creada
