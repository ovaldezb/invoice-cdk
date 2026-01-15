"""
Integration tests for genera_factura_handler - Happy Path.
IMPORTANT: Environment variables must be loaded BEFORE importing any handlers.
This test uses REAL SW Sapiens sandbox service (no mocks).
"""
import os
from pathlib import Path

# Load environment variables BEFORE any other imports
env_file = Path(__file__).parent.parent.parent / '.env_test'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Only set if not already set (don't override existing env vars)
                if key not in os.environ:
                    os.environ[key] = value.strip('"').strip("'")
else:
    raise FileNotFoundError(f"Required .env_test file not found at {env_file}")

# Store original directory and lambdas directory for later use
_original_dir = os.getcwd()
_lambdas_dir = Path(__file__).parent.parent.parent / 'invoice_cdk' / 'lambdas'

# Now we can safely import modules that depend on environment variables
import pytest
import json
from http import HTTPStatus
from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime, timezone
import uuid

# Import the actual handler (this will now work because env vars are loaded)
import invoice_cdk.lambdas.genera_factura_handler as genera_factura_handler


@pytest.fixture(scope='module')
def setup_working_directory():
    """Change to lambdas directory for PDF generator to find logo files"""
    original_dir = os.getcwd()
    os.chdir(_lambdas_dir)
    yield
    os.chdir(original_dir)


@pytest.fixture(scope='module')
def mongo_client(setup_working_directory):
    """Create MongoDB client for testing"""
    mongo_uri = os.environ.get('MONGODB_URI')
    if not mongo_uri:
        raise ValueError("MONGODB_URI environment variable is required for integration tests")
    client = MongoClient(mongo_uri)
    yield client
    client.close()


@pytest.fixture(scope='module')
def test_db(mongo_client):
    """Get test database"""
    db_name = os.environ.get('DB_NAME')
    if not db_name:
        raise ValueError("DB_NAME environment variable is required for integration tests")
    return mongo_client[db_name]


@pytest.fixture(scope='module')
def test_collections(test_db):
    """Get all required collections"""
    collections = {
        'facturas_emitidas': test_db['facturasemitidas'],
        'regimen_fiscal': test_db['regimenfiscal'],
        'folios': test_db['folios'],
        'ticket_timbrado': test_db['ticket_timbrado'],
        'serie_folio': test_db['serie_folio'],
        'bitacora': test_db['bitacora']
    }
    
    # Create unique index on ticket_timbrado.ticket to prevent duplicates
    # This is critical for preventing duplicate invoices from being generated
    try:
        collections['ticket_timbrado'].create_index("ticket", unique=True)
        print("✅ Created unique index on ticket_timbrado.ticket")
    except Exception as e:
        # Index already exists, which is fine
        print(f"ℹ️  Index on ticket_timbrado.ticket already exists: {e}")
    
    return collections


@pytest.fixture
def setup_test_data(test_collections):
    """Setup required test data in database"""
    # Generate TRULY unique ticket using timestamp + random to avoid SW Sapiens collisions
    # Format: TLE26262-XXXXXXX (where X is timestamp+random for uniqueness)
    import random
    import time
    timestamp_suffix = int(time.time() * 1000) % 10000000  # Last 7 digits of milliseconds
    random_suffix = random.randint(1000, 9999)
    test_ticket = f"TLE{timestamp_suffix}-{random_suffix}"
    print(f"\n🎫 Generated UNIQUE test ticket: {test_ticket}")
    test_sucursal = "182"
    
    # Setup: Ensure regimen fiscal exists (note: field name is "regimenfiscal" not "clave")
    regimen_fiscal_col = test_collections['regimen_fiscal']
    regimen_fiscal_col.update_one(
        {"regimenfiscal": "601"},
        {"$set": {"regimenfiscal": "601", "descripcion": "General de Ley Personas Morales"}},
        upsert=True
    )
    regimen_fiscal_col.update_one(
        {"regimenfiscal": "612"},
        {"$set": {"regimenfiscal": "612", "descripcion": "Personas Físicas con Actividades Empresariales y Profesionales"}},
        upsert=True
    )
    
    # Setup: Ensure folio exists for sucursal - ALWAYS reset to 1000 for clean test state
    folios_col = test_collections['folios']
    folios_col.update_one(
        {"sucursal": test_sucursal},
        {"$set": {"sucursal": test_sucursal, "noFolio": 1000}},
        upsert=True
    )
    
    # Clean serie_folio to prevent collisions from previous tests
    serie_folio_col = test_collections['serie_folio']
    serie_folio_col.delete_many({"folioTimbrado": {"$regex": "^OSFI"}})
    
    # Get current folio for validation later
    current_folio_doc = folios_col.find_one({"sucursal": test_sucursal})
    current_folio = current_folio_doc['noFolio']
    
    yield {
        'ticket': test_ticket,
        'sucursal': test_sucursal,
        'expected_folio': current_folio,
        'certificado_id': str(ObjectId())
    }
    
    # Cleanup: Remove test data
    # Note: Handler saves ticket WITH hyphens
    test_collections['ticket_timbrado'].delete_many({"ticket": test_ticket})
    test_collections['serie_folio'].delete_many({"folioTimbrado": {"$regex": f".*{current_folio}"}})
    test_collections['facturas_emitidas'].delete_many({"ticket": test_ticket})
    test_collections['bitacora'].delete_many({"ticket": test_ticket})


class TestGeneraFacturaHandlerIntegrationHappyPath:
    """Integration tests for genera_factura_handler - Happy Path scenario"""
    
    def test_genera_factura_happy_path_real_timbrado(self, test_collections, setup_test_data):
        """
        Test happy path: Successful invoice generation with REAL SW Sapiens sandbox.
        
        This test:
        1. Creates a valid timbrado request with real data
        2. Calls SW Sapiens sandbox service (REAL API call)
        3. Verifies the invoice is properly saved to database
        4. Validates PDF generation
        5. Checks bitacora entry
        """
        # Arrange: Prepare test data
        test_data = setup_test_data
        
        # Generate UNIQUE amounts to avoid SW Sapiens duplicate detection
        # SW Sapiens identifies duplicates by RFC+date+amounts, not just ticket
        import random
        import time
        unique_suffix = int(time.time()) % 10000  # Last 4 digits of timestamp
        base_amount = 24000.00 + (unique_suffix / 100)  # Range: 24000.00 to 24099.99
        iva = round(base_amount * 0.16, 2)
        total = round(base_amount + iva, 2)
        
        # Create timbrado data based on timbrado.json with UNIQUE amounts
        timbrado_data = {
            "Version": "4.0",
            "Serie": "OSFI",
            "Folio": "",
            "Fecha": "2025-11-25T10:00:00",
            "FormaPago": "04",
            "CondicionesDePago": "Un solo pago",
            "SubTotal": base_amount,
            "Descuento": 0,
            "Moneda": "MXN",
            "TipoCambio": 1,
            "Total": total,
            "TipoDeComprobante": "I",
            "Exportacion": "01",
            "MetodoPago": "PUE",
            "LugarExpedicion": "05109",
            "Emisor": {
                "Rfc": "FAR0010318A1",
                "Nombre": "FARZIN",
                "RegimenFiscal": "601"
            },
            "Receptor": {
                "Rfc": "EELD880811EJ6",
                "Nombre": "DANIEL ESPEJEL LUNA",
                "DomicilioFiscalReceptor": "01180",
                "RegimenFiscalReceptor": "612",
                "UsoCFDI": "G03"
            },
            "Conceptos": [
                {
                    "Impuestos": {
                        "Traslados": [
                            {
                                "Base": base_amount,
                                "Impuesto": "002",
                                "TipoFactor": "Tasa",
                                "TasaOCuota": "0.160000",
                                "Importe": iva
                            }
                        ]
                    },
                    "ClaveProdServ": "56101500",
                    "Cantidad": 1,
                    "ClaveUnidad": "H87",
                    "Unidad": "Pieza",
                    "Descripcion": "F-MUE-10010-U SALA MODULAR NAPOLES KF 8036 3.10 X 2.16",
                    "ValorUnitario": base_amount,
                    "Importe": base_amount,
                    "Descuento": 0,
                    "ObjetoImp": "02"
                }
            ],
            "Impuestos": {
                "Traslados": [
                    {
                        "Base": base_amount,
                        "Impuesto": "002",
                        "TipoFactor": "Tasa",
                        "TasaOCuota": "0.160000",
                        "Importe": iva
                    }
                ],
                "TotalImpuestosTrasladados": iva
            }
        }
        
        # Create the event body
        body = {
            "timbrado": timbrado_data,
            "sucursal": test_data['sucursal'],
            "ticket": test_data['ticket'],
            "idCertificado": test_data['certificado_id'],
            "fechaVenta": "2025-11-25T10:00:00",
            "email": "test@example.com",
            "direccion": "Calle Test 123, CDMX",
            "empresa": "FARZIN TEST"
        }
        
        # Create the Lambda event
        event = {
            "httpMethod": "POST",
            "body": json.dumps(body),
            "headers": {
                "Content-Type": "application/json",
                "origin": "http://localhost:4200"
            }
        }
        
        # Act: Call the handler (this will make REAL API calls to SW Sapiens sandbox)
        response = genera_factura_handler.handler(event, None)
        
        # Assert: Verify response
        assert response is not None, "Response should not be None"
        
        # Print response body if not 200 for debugging
        if response['statusCode'] != HTTPStatus.OK:
            print(f"\n❌ ERROR Response body: {response.get('body', 'No body')}")
        
        assert response['statusCode'] == HTTPStatus.OK, f"Expected 200 OK, got {response['statusCode']}"
        
        # Parse response body
        response_body = json.loads(response['body'])
        
        # Verify CFDI was generated
        assert 'cfdi' in response_body, "Response should contain CFDI XML"
        assert 'uuid' in response_body, "Response should contain UUID"
        assert 'qrCode' in response_body, "Response should contain QR code"
        assert 'cadenaOriginalSAT' in response_body, "Response should contain cadena original SAT"
        assert 'pdf_cfdi_b64' in response_body, "Response should contain PDF in base64"
        
        # Verify UUID format (should be a valid UUID)
        uuid_value = response_body['uuid']
        assert len(uuid_value) == 36, f"UUID should be 36 characters, got {len(uuid_value)}"
        assert uuid_value.count('-') == 4, "UUID should have 4 hyphens"
        
        # Verify folio was assigned
        assert response_body.get('sucursal') == test_data['sucursal'], "Sucursal should match"
        assert response_body.get('ticket') == test_data['ticket'], "Ticket should match"
        
        # Verify factura was saved to database
        factura_saved = test_collections['facturas_emitidas'].find_one({"ticket": test_data['ticket']})
        assert factura_saved is not None, "Factura should be saved in database"
        assert factura_saved['uuid'] == uuid_value, "Saved UUID should match response UUID"
        assert factura_saved['estatus'] == "Vigente", "Factura status should be 'Vigente'"
        assert factura_saved['idCertificado'] == test_data['certificado_id'], "Certificate ID should match"
        
        # Verify ticket_timbrado was created
        # Note: Handler saves ticket WITHOUT hyphens
        ticket_timbrado = test_collections['ticket_timbrado'].find_one({
            "ticket": test_data['ticket'].replace("-", "")  # Search WITHOUT hyphens
        })
        assert ticket_timbrado is not None, "Ticket timbrado should be registered"
        
        # Extract the actual folio used from the CFDI XML in the response
        # Parse the CFDI XML to get Serie and Folio
        import xml.etree.ElementTree as ET
        cfdi_xml = response_body['cfdi']
        root = ET.fromstring(cfdi_xml)
        # Extract Serie and Folio attributes from root element
        serie_used = root.attrib.get('Serie', '')
        folio_used = root.attrib.get('Folio', '')
        
        print(f"\n🔍 DEBUG: Serie used = {serie_used}, Folio used = {folio_used}")
        
        # The handler uses the current folio without incrementing it (unless there's a duplicate)
        # Verify serie_folio was created using the actual folio from the invoice
        folio_timbrado_expected = f"{serie_used}{folio_used}"
        serie_folio = test_collections['serie_folio'].find_one({
            "folioTimbrado": folio_timbrado_expected
        })
        assert serie_folio is not None, f"Serie folio '{folio_timbrado_expected}' should be registered"
        
        # Verify bitacora entry (success)
        bitacora_entry = test_collections['bitacora'].find_one({
            "ticket": test_data['ticket'],
            "status": "exito"
        })
        assert bitacora_entry is not None, "Success bitacora entry should exist"
        assert "Factura generada exitosamente" in bitacora_entry['mensaje'], "Success message should be logged"
        assert bitacora_entry['rfc'] == "EELD880811EJ6", "RFC should match receptor"
        assert bitacora_entry['rfcEmisor'] == "FAR0010318A1", "RFC Emisor should match"
        
        # Verify PDF was generated (base64 encoded)
        pdf_b64 = response_body['pdf_cfdi_b64']
        assert len(pdf_b64) > 1000, "PDF should be substantial size"
        assert pdf_b64.startswith("JVBERi0"), "PDF should start with PDF header (base64 encoded)"
        
        print(f"\n✅ Happy path test passed successfully!")
        print(f"   UUID: {uuid_value}")
        print(f"   Ticket: {test_data['ticket']}")
        print(f"   Folio: {folio_used}")
        print(f"   PDF size: {len(pdf_b64)} bytes")


class TestGeneraFacturaHandlerIntegrationErrors:
    """Integration tests for genera_factura_handler - Error scenarios"""
    
    def test_genera_factura_cp_invalido(self, test_collections, setup_test_data):
        """
        Test error handling: Invalid postal code (CP) for receptor.
        
        This test:
        1. Creates a timbrado request with invalid CP (00000)
        2. Calls SW Sapiens sandbox service (REAL API call)
        3. Verifies that SW Sapiens returns an error
        4. Checks that the error message is properly captured
        5. Validates that bitacora logs the error
        6. Ensures folio was NOT consumed (rollback)
        """
        # Arrange: Prepare test data with INVALID CP
        test_data = setup_test_data
        
        # Get current folio BEFORE the failed operation
        initial_folio_doc = test_collections['folios'].find_one({"sucursal": test_data['sucursal']})
        initial_folio = initial_folio_doc['noFolio']
        
        # Create timbrado data with INVALID postal code
        timbrado_data = {
            "Version": "4.0",
            "Serie": "OSFI",
            "Folio": "",
            "Fecha": "2025-11-25T10:00:00",
            "FormaPago": "04",
            "CondicionesDePago": "Un solo pago",
            "SubTotal": 1000.00,
            "Descuento": 0,
            "Moneda": "MXN",
            "TipoCambio": 1,
            "Total": 1160.00,
            "TipoDeComprobante": "I",
            "Exportacion": "01",
            "MetodoPago": "PUE",
            "LugarExpedicion": "05109",
            "Emisor": {
                "Rfc": "FAR0010318A1",
                "Nombre": "FARZIN",
                "RegimenFiscal": "601"
            },
            "Receptor": {
                "Rfc": "EELD880811EJ6",
                "Nombre": "DANIEL ESPEJEL LUNA",
                "DomicilioFiscalReceptor": "00000",  # INVALID CP
                "RegimenFiscalReceptor": "612",
                "UsoCFDI": "G03"
            },
            "Conceptos": [
                {
                    "Impuestos": {
                        "Traslados": [
                            {
                                "Base": 1000.00,
                                "Impuesto": "002",
                                "TipoFactor": "Tasa",
                                "TasaOCuota": "0.160000",
                                "Importe": 160.00
                            }
                        ]
                    },
                    "ClaveProdServ": "56101500",
                    "Cantidad": 1,
                    "ClaveUnidad": "H87",
                    "Unidad": "Pieza",
                    "Descripcion": "PRODUCTO DE PRUEBA",
                    "ValorUnitario": 1000.00,
                    "Importe": 1000.00,
                    "Descuento": 0,
                    "ObjetoImp": "02"
                }
            ],
            "Impuestos": {
                "Traslados": [
                    {
                        "Base": 1000.00,
                        "Impuesto": "002",
                        "TipoFactor": "Tasa",
                        "TasaOCuota": "0.160000",
                        "Importe": 160.00
                    }
                ],
                "TotalImpuestosTrasladados": 160.00
            }
        }
        
        # Create the event body
        body = {
            "timbrado": timbrado_data,
            "sucursal": test_data['sucursal'],
            "ticket": test_data['ticket'],
            "idCertificado": test_data['certificado_id'],
            "fechaVenta": "2025-11-25T10:00:00",
            "email": "test@example.com",
            "direccion": "Calle Test 123, CDMX",
            "empresa": "FARZIN TEST"
        }
        
        # Create the Lambda event
        event = {
            "httpMethod": "POST",
            "body": json.dumps(body),
            "headers": {
                "Content-Type": "application/json",
                "origin": "http://localhost:4200"
            }
        }
        
        # Act: Call the handler (this will make REAL API call to SW Sapiens sandbox)
        response = genera_factura_handler.handler(event, None)
        
        # Assert: Verify error response
        assert response is not None, "Response should not be None"
        assert response['statusCode'] == HTTPStatus.BAD_REQUEST, \
            f"Expected 400 BAD_REQUEST for SW Sapiens validation error, got {response['statusCode']}"
        
        # Parse response body
        response_body = json.loads(response['body'])
        
        # Verify error message is present
        # Handler returns error in 'message' key for BAD_REQUEST errors
        assert 'message' in response_body, "Response should contain message key"
        error_message = response_body['message']
        
        # SW Sapiens should return error about invalid CP
        # Common error messages from SW Sapiens for invalid CP:
        # - "El código postal no existe en el catálogo"
        # - "DomicilioFiscalReceptor"
        # - "CFDI40156"
        assert any(keyword in error_message.lower() for keyword in [
            'código postal',
            'domiciliofiscalreceptor',
            'cfdi40156',
            'postal',
            'cp',
            '00000'
        ]), f"Error message should mention postal code issue. Got: {error_message}"
        
        # Verify folio was NOT consumed (rollback happened)
        final_folio_doc = test_collections['folios'].find_one({"sucursal": test_data['sucursal']})
        final_folio = final_folio_doc['noFolio']
        assert final_folio == initial_folio, \
            f"Folio should NOT be incremented on error. Initial: {initial_folio}, Final: {final_folio}"
        
        # Verify NO factura was saved to database
        factura_saved = test_collections['facturas_emitidas'].find_one({"ticket": test_data['ticket']})
        assert factura_saved is None, "Factura should NOT be saved on error"
        
        # Verify ticket_timbrado was NOT created (or was rolled back)
        # Handler saves ticket WITHOUT hyphens for deduplication
        ticket_timbrado = test_collections['ticket_timbrado'].find_one({
            "ticket": test_data['ticket'].replace("-", "")
        })
        assert ticket_timbrado is None, "Ticket timbrado should NOT exist after rollback"
        
        # Verify bitacora entry (error logged)
        bitacora_entry = test_collections['bitacora'].find_one({
            "ticket": test_data['ticket'],
            "status": "error"
        })
        assert bitacora_entry is not None, "Error bitacora entry should exist"
        assert error_message in bitacora_entry['mensaje'], \
            "Bitacora should contain the error message from SW Sapiens"
        assert bitacora_entry['rfc'] == "EELD880811EJ6", "RFC should match receptor"
        assert bitacora_entry['rfcEmisor'] == "FAR0010318A1", "RFC Emisor should match"
        
        print(f"\n✅ Invalid CP test passed successfully!")
        print(f"   Ticket: {test_data['ticket']}")
        print(f"   Error captured: {error_message[:100]}...")
        print(f"   Folio preserved: {final_folio} (not incremented)")
        print(f"   Bitacora logged: ✓")
    
    def test_genera_factura_ticket_duplicado(self, test_collections, setup_test_data):
        """
        Test error handling: Duplicate ticket (trying to stamp the same ticket twice).
        
        This test:
        1. Creates a valid timbrado request with a unique ticket
        2. Successfully timbres the invoice (first attempt)
        3. Tries to timbre the SAME ticket again (second attempt)
        4. Verifies that the second attempt returns an error
        5. Checks that the error message indicates duplicate ticket
        6. Validates that only ONE factura exists in database
        7. Ensures folio was consumed only ONCE
        """
        # Arrange: Generate unique ticket for this test with realistic format
        # Format: TLE26262-XXXXXXX (where X is a random number)
        import random
        import time
        test_ticket = f"TLE26262-{random.randint(1000000, 9999999)}"
        test_sucursal = "182"
        test_certificado_id = str(ObjectId())
        
        # Generate UNIQUE amounts to avoid SW Sapiens duplicate detection
        unique_suffix = int(time.time()) % 10000
        base_amount = 1000.00 + (unique_suffix / 100)
        iva = round(base_amount * 0.16, 2)
        total = round(base_amount + iva, 2)
        
        # Get current folio BEFORE operations
        initial_folio_doc = test_collections['folios'].find_one({"sucursal": test_sucursal})
        initial_folio = initial_folio_doc['noFolio']
        
        # Create valid timbrado data with UNIQUE amounts
        timbrado_data = {
            "Version": "4.0",
            "Serie": "OSFI",
            "Folio": "",
            "Fecha": "2025-11-25T10:00:00",
            "FormaPago": "04",
            "CondicionesDePago": "Un solo pago",
            "SubTotal": base_amount,
            "Descuento": 0,
            "Moneda": "MXN",
            "TipoCambio": 1,
            "Total": total,
            "TipoDeComprobante": "I",
            "Exportacion": "01",
            "MetodoPago": "PUE",
            "LugarExpedicion": "05109",
            "Emisor": {
                "Rfc": "FAR0010318A1",
                "Nombre": "FARZIN",
                "RegimenFiscal": "601"
            },
            "Receptor": {
                "Rfc": "EELD880811EJ6",
                "Nombre": "DANIEL ESPEJEL LUNA",
                "DomicilioFiscalReceptor": "01180",
                "RegimenFiscalReceptor": "612",
                "UsoCFDI": "G03"
            },
            "Conceptos": [
                {
                    "Impuestos": {
                        "Traslados": [
                            {
                                "Base": base_amount,
                                "Impuesto": "002",
                                "TipoFactor": "Tasa",
                                "TasaOCuota": "0.160000",
                                "Importe": iva
                            }
                        ]
                    },
                    "ClaveProdServ": "56101500",
                    "Cantidad": 1,
                    "ClaveUnidad": "H87",
                    "Unidad": "Pieza",
                    "Descripcion": "PRODUCTO DE PRUEBA DUPLICADO",
                    "ValorUnitario": base_amount,
                    "Importe": base_amount,
                    "Descuento": 0,
                    "ObjetoImp": "02"
                }
            ],
            "Impuestos": {
                "Traslados": [
                    {
                        "Base": base_amount,
                        "Impuesto": "002",
                        "TipoFactor": "Tasa",
                        "TasaOCuota": "0.160000",
                        "Importe": iva
                    }
                ],
                "TotalImpuestosTrasladados": iva
            }
        }
        
        # Create the event body
        body = {
            "timbrado": timbrado_data,
            "sucursal": test_sucursal,
            "ticket": test_ticket,
            "idCertificado": test_certificado_id,
            "fechaVenta": "2025-11-25T10:00:00",
            "email": "test@example.com",
            "direccion": "Calle Test 123, CDMX",
            "empresa": "FARZIN TEST"
        }
        
        # Create the Lambda event
        event = {
            "httpMethod": "POST",
            "body": json.dumps(body),
            "headers": {
                "Content-Type": "application/json",
                "origin": "http://localhost:4200"
            }
        }
        
        try:
            # Act 1: First attempt - Should succeed
            print(f"\n🔄 First attempt: Timbring ticket {test_ticket}...")
            response1 = genera_factura_handler.handler(event, None)
            
            # Assert 1: First attempt should be successful
            assert response1 is not None, "First response should not be None"
            assert response1['statusCode'] == HTTPStatus.OK, \
                f"First attempt should succeed with 200 OK, got {response1['statusCode']}"
            
            response1_body = json.loads(response1['body'])
            uuid1 = response1_body.get('uuid')
            assert uuid1 is not None, "First attempt should return UUID"
            
            # Get folio after first attempt
            folio_after_first = test_collections['folios'].find_one({"sucursal": test_sucursal})['noFolio']
            
            print(f"✅ First attempt succeeded!")
            print(f"   UUID: {uuid1}")
            print(f"   Folio used: {folio_after_first - 1}")
            
            # Act 2: Second attempt - Should fail (duplicate ticket)
            print(f"\n🔄 Second attempt: Trying to timbre SAME ticket {test_ticket}...")
            response2 = genera_factura_handler.handler(event, None)
            
            # Assert 2: Second attempt should fail with error
            assert response2 is not None, "Second response should not be None"
            assert response2['statusCode'] == HTTPStatus.INTERNAL_SERVER_ERROR, \
                f"Second attempt should fail with 500, got {response2['statusCode']}"
            
            response2_body = json.loads(response2['body'])
            assert 'message' in response2_body, "Second attempt should return message key (not error)"
            
            error_message = response2_body['message']
            
            # Verify error message mentions duplicate/already timbrado
            assert any(keyword in error_message.lower() for keyword in [
                'duplicado',
                'timbrado',
                'existe',
                'ya fue timbrado',
                'already',
                'duplicate'
            ]), f"Error should indicate duplicate ticket. Got: {error_message}"
            
            print(f"✅ Second attempt correctly rejected!")
            print(f"   Error: {error_message[:100]}...")
            
            # Verify folio was NOT consumed in second attempt
            folio_after_second = test_collections['folios'].find_one({"sucursal": test_sucursal})['noFolio']
            assert folio_after_second == folio_after_first, \
                f"Folio should NOT be incremented on duplicate. After first: {folio_after_first}, After second: {folio_after_second}"
            
            # Verify only ONE factura exists
            facturas_count = test_collections['facturas_emitidas'].count_documents({"ticket": test_ticket})
            assert facturas_count == 1, f"Should have exactly ONE factura, found {facturas_count}"
            
            # Verify only ONE ticket_timbrado exists
            # Handler saves ticket WITHOUT hyphens for deduplication
            ticket_timbrado_count = test_collections['ticket_timbrado'].count_documents({
                "ticket": test_ticket.replace("-", "")
            })
            assert ticket_timbrado_count == 1, \
                f"Should have exactly ONE ticket_timbrado, found {ticket_timbrado_count}"
            
            # Verify bitacora entries
            bitacora_success = test_collections['bitacora'].find_one({
                "ticket": test_ticket,
                "status": "exito"
            })
            assert bitacora_success is not None, "Success bitacora should exist from first attempt"
            
            bitacora_error = test_collections['bitacora'].find_one({
                "ticket": test_ticket,
                "status": "error"
            })
            assert bitacora_error is not None, "Error bitacora should exist from second attempt"
            assert "duplicado" in bitacora_error['mensaje'].lower() or "timbrado" in bitacora_error['mensaje'].lower(), \
                "Error bitacora should mention duplicate/timbrado"
            
            print(f"\n✅ Duplicate ticket test passed successfully!")
            print(f"   Ticket: {test_ticket}")
            print(f"   First attempt: SUCCESS (UUID: {uuid1})")
            print(f"   Second attempt: REJECTED (Duplicate)")
            print(f"   Folio consumed: 1 time only (folio {folio_after_first - 1})")
            print(f"   Facturas in DB: 1")
            print(f"   Bitacora entries: 2 (1 success, 1 error)")
            
        finally:
            # Cleanup: Remove test data
            # Note: Handler saves ticket WITH hyphens
            test_collections['ticket_timbrado'].delete_many({"ticket": test_ticket})
            test_collections['serie_folio'].delete_many({"folioTimbrado": {"$regex": f".*OSFI.*"}})
            test_collections['facturas_emitidas'].delete_many({"ticket": test_ticket})
            test_collections['bitacora'].delete_many({"ticket": test_ticket})
    
    def test_genera_factura_folio_rollback_on_error(self, test_collections, setup_test_data):
        """
        Test folio rollback: When timbrado fails, folio should be decremented to be reused.
        
        This test:
        1. Gets the current folio number
        2. Attempts to timbre an invoice with invalid data (will fail)
        3. Verifies that the error occurred
        4. Checks that the folio was decremented (rolled back)
        5. Attempts to timbre again with VALID data
        6. Verifies that the SAME folio is reused successfully
        """
        # Arrange: Generate unique tickets for this test
        import random
        import time
        test_ticket_fail = f"TLE26262-{random.randint(1000000, 9999999)}"
        test_ticket_success = f"TLE26262-{random.randint(1000000, 9999999)}"
        test_sucursal = "182"
        test_certificado_id = str(ObjectId())
        
        # Generate UNIQUE amounts to avoid SW Sapiens duplicate detection
        unique_suffix = int(time.time()) % 10000
        base_amount = 1000.00 + (unique_suffix / 100)
        iva = round(base_amount * 0.16, 2)
        total = round(base_amount + iva, 2)
        
        # CRITICAL: Clean serie_folio to prevent while loop collisions
        # This ensures the folio won't increment multiple times during the first attempt
        delete_result = test_collections['serie_folio'].delete_many({"folioTimbrado": {"$regex": "^OSFI"}})
        print(f"\n🧹 Cleaned {delete_result.deleted_count} records from serie_folio")
        
        # Get INITIAL folio BEFORE any operations
        initial_folio_doc = test_collections['folios'].find_one({"sucursal": test_sucursal})
        initial_folio = initial_folio_doc['noFolio']
        
        print(f"\n📊 Initial state:")
        print(f"   Folio before operations: {initial_folio}")
        
        # Create timbrado data with INVALID CP (will cause SW Sapiens error) and UNIQUE amounts
        timbrado_data_fail = {
            "Version": "4.0",
            "Serie": "OSFI",
            "Folio": "",
            "Fecha": "2025-11-25T10:00:00",
            "FormaPago": "04",
            "CondicionesDePago": "Un solo pago",
            "SubTotal": base_amount,
            "Descuento": 0,
            "Moneda": "MXN",
            "TipoCambio": 1,
            "Total": total,
            "TipoDeComprobante": "I",
            "Exportacion": "01",
            "MetodoPago": "PUE",
            "LugarExpedicion": "05109",
            "Emisor": {
                "Rfc": "FAR0010318A1",
                "Nombre": "FARZIN",
                "RegimenFiscal": "601"
            },
            "Receptor": {
                "Rfc": "EELD880811EJ6",
                "Nombre": "DANIEL ESPEJEL LUNA",
                "DomicilioFiscalReceptor": "00000",  # INVALID CP - will cause error
                "RegimenFiscalReceptor": "612",
                "UsoCFDI": "G03"
            },
            "Conceptos": [
                {
                    "Impuestos": {
                        "Traslados": [
                            {
                                "Base": base_amount,
                                "Impuesto": "002",
                                "TipoFactor": "Tasa",
                                "TasaOCuota": "0.160000",
                                "Importe": iva
                            }
                        ]
                    },
                    "ClaveProdServ": "56101500",
                    "Cantidad": 1,
                    "ClaveUnidad": "H87",
                    "Unidad": "Pieza",
                    "Descripcion": "PRODUCTO FOLIO ROLLBACK TEST",
                    "ValorUnitario": base_amount,
                    "Importe": base_amount,
                    "Descuento": 0,
                    "ObjetoImp": "02"
                }
            ],
            "Impuestos": {
                "Traslados": [
                    {
                        "Base": base_amount,
                        "Impuesto": "002",
                        "TipoFactor": "Tasa",
                        "TasaOCuota": "0.160000",
                        "Importe": iva
                    }
                ],
                "TotalImpuestosTrasladados": iva
            }
        }
        
        # Create valid timbrado data (for second attempt)
        timbrado_data_success = timbrado_data_fail.copy()
        timbrado_data_success["Receptor"] = {
            "Rfc": "EELD880811EJ6",
            "Nombre": "DANIEL ESPEJEL LUNA",
            "DomicilioFiscalReceptor": "01180",  # VALID CP
            "RegimenFiscalReceptor": "612",
            "UsoCFDI": "G03"
        }
        
        try:
            # Act 1: First attempt with INVALID data - Should FAIL
            print(f"\n🔄 First attempt (will fail): Ticket {test_ticket_fail} with INVALID CP...")
            
            body_fail = {
                "timbrado": timbrado_data_fail,
                "sucursal": test_sucursal,
                "ticket": test_ticket_fail,
                "idCertificado": test_certificado_id,
                "fechaVenta": "2025-11-25T10:00:00",
                "email": "test@example.com",
                "direccion": "Calle Test 123, CDMX",
                "empresa": "FARZIN TEST"
            }
            
            event_fail = {
                "httpMethod": "POST",
                "body": json.dumps(body_fail),
                "headers": {
                    "Content-Type": "application/json",
                    "origin": "http://localhost:4200"
                }
            }
            
            response_fail = genera_factura_handler.handler(event_fail, None)
            
            # Assert 1: First attempt should FAIL
            assert response_fail is not None, "Response should not be None"
            assert response_fail['statusCode'] == HTTPStatus.BAD_REQUEST, \
                f"First attempt should fail with 400, got {response_fail['statusCode']}"
            
            response_fail_body = json.loads(response_fail['body'])
            error_message = response_fail_body.get('message', '')
            
            print(f"❌ First attempt failed as expected!")
            print(f"   Error: {error_message[:100]}...")
            
            # Get folio AFTER failed attempt
            folio_after_fail = test_collections['folios'].find_one({"sucursal": test_sucursal})['noFolio']
            
            # Assert: Folio should be DECREMENTED (rolled back) to initial value
            assert folio_after_fail == initial_folio, \
                f"Folio should be rolled back to initial value. Initial: {initial_folio}, After fail: {folio_after_fail}"
            
            print(f"✅ Folio correctly rolled back!")
            print(f"   Folio after error: {folio_after_fail} (same as initial: {initial_folio})")
            
            # Act 2: Second attempt with VALID data - Should SUCCEED and use SAME folio
            print(f"\n🔄 Second attempt (will succeed): Ticket {test_ticket_success} with VALID CP...")
            
            body_success = {
                "timbrado": timbrado_data_success,
                "sucursal": test_sucursal,
                "ticket": test_ticket_success,
                "idCertificado": test_certificado_id,
                "fechaVenta": "2025-11-25T10:00:00",
                "email": "test@example.com",
                "direccion": "Calle Test 123, CDMX",
                "empresa": "FARZIN TEST"
            }
            
            event_success = {
                "httpMethod": "POST",
                "body": json.dumps(body_success),
                "headers": {
                    "Content-Type": "application/json",
                    "origin": "http://localhost:4200"
                }
            }
            
            response_success = genera_factura_handler.handler(event_success, None)
            
            # Assert 2: Second attempt should SUCCEED
            assert response_success is not None, "Response should not be None"
            assert response_success['statusCode'] == HTTPStatus.OK, \
                f"Second attempt should succeed with 200, got {response_success['statusCode']}"
            
            response_success_body = json.loads(response_success['body'])
            uuid_success = response_success_body.get('uuid')
            
            # Get the factura from database to check which folio was used
            factura_success = test_collections['facturas_emitidas'].find_one({'uuid': uuid_success})
            
            # Extract folio from CFDI XML
            folio_used = None
            if factura_success and 'cfdi' in factura_success:
                import re
                # Parse folio from CFDI XML: Folio="1013"
                folio_match = re.search(r'Folio="(\d+)"', factura_success['cfdi'])
                if folio_match:
                    folio_used = folio_match.group(1)
            
            print(f"✅ Second attempt succeeded!")
            print(f"   UUID: {uuid_success}")
            print(f"   Folio used: {folio_used}")
            
            # Get folio AFTER successful attempt
            folio_after_success = test_collections['folios'].find_one({"sucursal": test_sucursal})['noFolio']
            
            # Assert: Folio should now be incremented (initial + 1)
            assert folio_after_success == initial_folio + 1, \
                f"Folio should be incremented after success. Initial: {initial_folio}, After success: {folio_after_success}"
            
            # Assert: The folio USED in successful attempt should be the SAME as initial
            assert folio_used == str(initial_folio), \
                f"Folio used should be the rolled-back folio. Expected: {initial_folio}, Used: {folio_used}"
            
            # Verify factura was saved with correct folio
            factura_saved = test_collections['facturas_emitidas'].find_one({"ticket": test_ticket_success})
            assert factura_saved is not None, "Factura should be saved"
            
            # Note: folio is embedded in CFDI XML, not as a separate field
            # Parse it from XML
            import re
            factura_folio_match = re.search(r'Folio="(\d+)"', factura_saved['cfdi'])
            factura_folio = factura_folio_match.group(1) if factura_folio_match else None
            assert factura_folio == str(initial_folio), \
                f"Saved factura should have rolled-back folio. Expected: {initial_folio}, Got: {factura_folio}"
            
            # Verify serie_folio was created with correct folio
            serie_folio = test_collections['serie_folio'].find_one({
                "folioTimbrado": {"$regex": f".*{initial_folio}"}
            })
            assert serie_folio is not None, "Serie folio should exist with rolled-back folio"
            
            # Verify bitacora entries
            bitacora_fail = test_collections['bitacora'].find_one({
                "ticket": test_ticket_fail,
                "status": "error"
            })
            assert bitacora_fail is not None, "Error bitacora should exist from first attempt"
            
            bitacora_success = test_collections['bitacora'].find_one({
                "ticket": test_ticket_success,
                "status": "exito"
            })
            assert bitacora_success is not None, "Success bitacora should exist from second attempt"
            
            print(f"\n✅ Folio rollback test passed successfully!")
            print(f"   Initial folio: {initial_folio}")
            print(f"   After failed attempt: {folio_after_fail} (rolled back)")
            print(f"   Folio used in success: {folio_used} (reused rolled-back folio)")
            print(f"   After successful attempt: {folio_after_success} (incremented)")
            print(f"   Ticket failed: {test_ticket_fail}")
            print(f"   Ticket success: {test_ticket_success}")
            
        finally:
            # Cleanup: Remove test data
            test_collections['ticket_timbrado'].delete_many({
                "ticket": {"$in": [test_ticket_fail.replace("-", ""), test_ticket_success.replace("-", "")]}
            })
            test_collections['serie_folio'].delete_many({"folioTimbrado": {"$regex": f".*OSFI.*"}})
            test_collections['facturas_emitidas'].delete_many({
                "ticket": {"$in": [test_ticket_fail, test_ticket_success]}
            })
            test_collections['bitacora'].delete_many({
                "ticket": {"$in": [test_ticket_fail, test_ticket_success]}
            })
    
    def test_genera_factura_similar_tickets_success(self, test_collections, setup_test_data):
        """
        Test that two tickets with similar numbers (same suffix, different prefix) 
        can both be stamped successfully without conflicts.
        
        Example tickets:
        - TLE26198-1528825
        - TLE26210-1528825
        
        Both should succeed and use consecutive folios.
        """
        print("\n" + "="*80)
        print("TEST: Similar Ticket Numbers - Both Should Succeed")
        print("="*80)
        
        # Setup test data
        test_sucursal = "182"
        test_certificado_id = str(ObjectId())
        
        # Generate UNIQUE amounts to avoid SW Sapiens duplicate detection
        import time
        unique_suffix = int(time.time()) % 10000
        base_amount = 1000.00 + (unique_suffix / 100)
        iva = round(base_amount * 0.16, 2)
        total = round(base_amount + iva, 2)
        
        # Generate two similar ticket numbers with same suffix
        import random
        suffix = str(random.randint(1000000, 9999999))
        prefix1 = "TLE26198"
        prefix2 = "TLE26210"
        
        test_ticket_1 = f"{prefix1}-{suffix}"
        test_ticket_2 = f"{prefix2}-{suffix}"
        
        print(f"\n📋 Test tickets:")
        print(f"   Ticket 1: {test_ticket_1}")
        print(f"   Ticket 2: {test_ticket_2}")
        print(f"   (Same suffix: {suffix}, different prefixes)")
        
        # Note: Index on ticket_timbrado.ticket is already created in test_collections fixture
        
        # Get initial folio
        initial_folio = test_collections['folios'].find_one({"sucursal": test_sucursal})['noFolio']
        
        print(f"\n📊 Initial state:")
        print(f"   Initial folio: {initial_folio}")
        
        # Prepare timbrado data for FIRST ticket with UNIQUE amounts and ALL required fields
        timbrado_data_1 = {
            "Version": "4.0",
            "Serie": "OSFI",
            "Folio": "",
            "Fecha": "2025-11-25T10:00:00",
            "FormaPago": "04",
            "CondicionesDePago": "Un solo pago",
            "SubTotal": base_amount,
            "Descuento": 0,
            "Moneda": "MXN",
            "TipoCambio": 1,
            "Total": total,
            "TipoDeComprobante": "I",
            "Exportacion": "01",
            "MetodoPago": "PUE",
            "LugarExpedicion": "05109",
            "Emisor": {
                "Rfc": "FAR0010318A1",
                "Nombre": "FARZIN",
                "RegimenFiscal": "601"
            },
            "Receptor": {
                "Rfc": "EELD880811EJ6",
                "Nombre": "DANIEL ESPEJEL LUNA",
                "DomicilioFiscalReceptor": "01180",
                "RegimenFiscalReceptor": "612",
                "UsoCFDI": "G03"
            },
            "Conceptos": [{
                "Impuestos": {
                    "Traslados": [{
                        "Base": base_amount,
                        "Impuesto": "002",
                        "TipoFactor": "Tasa",
                        "TasaOCuota": "0.160000",
                        "Importe": iva
                    }]
                },
                "ClaveProdServ": "56101500",
                "Cantidad": 1,
                "ClaveUnidad": "H87",
                "Unidad": "Pieza",
                "Descripcion": "PRODUCTO SIMILAR TICKET 1",
                "ValorUnitario": base_amount,
                "Importe": base_amount,
                "Descuento": 0,
                "ObjetoImp": "02"
            }],
            "Impuestos": {
                "Traslados": [{
                    "Base": base_amount,
                    "Impuesto": "002",
                    "TipoFactor": "Tasa",
                    "TasaOCuota": "0.160000",
                    "Importe": iva
                }],
                "TotalImpuestosTrasladados": iva
            }
        }
        
        # Prepare timbrado data for SECOND ticket (slightly different amount to avoid SW duplicate)
        base_amount_2 = base_amount + 1.00  # Add 1 peso to differentiate
        iva_2 = round(base_amount_2 * 0.16, 2)
        total_2 = round(base_amount_2 + iva_2, 2)
        
        timbrado_data_2 = {
            "Version": "4.0",
            "Serie": "OSFI",
            "Folio": "",
            "Fecha": "2025-11-25T10:00:00",
            "FormaPago": "04",
            "CondicionesDePago": "Un solo pago",
            "SubTotal": base_amount_2,
            "Descuento": 0,
            "Moneda": "MXN",
            "TipoCambio": 1,
            "Total": total_2,
            "TipoDeComprobante": "I",
            "Exportacion": "01",
            "MetodoPago": "PUE",
            "LugarExpedicion": "05109",
            "Emisor": {
                "Rfc": "FAR0010318A1",
                "Nombre": "FARZIN",
                "RegimenFiscal": "601"
            },
            "Receptor": {
                "Rfc": "EELD880811EJ6",
                "Nombre": "DANIEL ESPEJEL LUNA",
                "DomicilioFiscalReceptor": "01180",
                "RegimenFiscalReceptor": "612",
                "UsoCFDI": "G03"
            },
            "Conceptos": [{
                "Impuestos": {
                    "Traslados": [{
                        "Base": base_amount_2,
                        "Impuesto": "002",
                        "TipoFactor": "Tasa",
                        "TasaOCuota": "0.160000",
                        "Importe": iva_2
                    }]
                },
                "ClaveProdServ": "56101500",
                "Cantidad": 1,
                "ClaveUnidad": "H87",
                "Unidad": "Pieza",
                "Descripcion": "PRODUCTO SIMILAR TICKET 2",
                "ValorUnitario": base_amount_2,
                "Importe": base_amount_2,
                "Descuento": 0,
                "ObjetoImp": "02"
            }],
            "Impuestos": {
                "Traslados": [{
                    "Base": base_amount_2,
                    "Impuesto": "002",
                    "TipoFactor": "Tasa",
                    "TasaOCuota": "0.160000",
                    "Importe": iva_2
                }],
                "TotalImpuestosTrasladados": iva_2
            }
        }
        
        try:
            # Act 1: Stamp FIRST ticket
            print(f"\n🔄 First stamp: Ticket {test_ticket_1}...")
            
            body_1 = {
                "timbrado": timbrado_data_1,
                "sucursal": test_sucursal,
                "ticket": test_ticket_1,
                "idCertificado": test_certificado_id,
                "fechaVenta": "2025-11-25T10:00:00",
                "email": "test@example.com",
                "direccion": "Calle Test 123, CDMX",
                "empresa": "FARZIN TEST"
            }
            
            event_1 = {
                "httpMethod": "POST",
                "body": json.dumps(body_1),
                "headers": {
                    "Content-Type": "application/json",
                    "origin": "http://localhost:4200"
                }
            }
            
            response_1 = genera_factura_handler.handler(event_1, None)
            
            # Assert 1: First stamp should SUCCEED
            assert response_1 is not None, "Response 1 should not be None"
            assert response_1['statusCode'] == HTTPStatus.OK, \
                f"First stamp should succeed with 200, got {response_1['statusCode']}"
            
            response_1_body = json.loads(response_1['body'])
            uuid_1 = response_1_body.get('uuid')
            
            # Extract folio from first factura
            factura_1 = test_collections['facturas_emitidas'].find_one({'uuid': uuid_1})
            folio_1 = None
            if factura_1 and 'cfdi' in factura_1:
                import re
                folio_match = re.search(r'Folio="(\d+)"', factura_1['cfdi'])
                if folio_match:
                    folio_1 = folio_match.group(1)
            
            print(f"✅ First stamp succeeded!")
            print(f"   UUID: {uuid_1}")
            print(f"   Folio: {folio_1}")
            
            # Get folio after first stamp
            folio_after_first = test_collections['folios'].find_one({"sucursal": test_sucursal})['noFolio']
            
            # Act 2: Stamp SECOND ticket with similar number
            print(f"\n🔄 Second stamp: Ticket {test_ticket_2}...")
            
            body_2 = {
                "timbrado": timbrado_data_2,
                "sucursal": test_sucursal,
                "ticket": test_ticket_2,
                "idCertificado": test_certificado_id,
                "fechaVenta": "2025-11-25T10:00:00",
                "email": "test@example.com",
                "direccion": "Calle Test 123, CDMX",
                "empresa": "FARZIN TEST"
            }
            
            event_2 = {
                "httpMethod": "POST",
                "body": json.dumps(body_2),
                "headers": {
                    "Content-Type": "application/json",
                    "origin": "http://localhost:4200"
                }
            }
            
            response_2 = genera_factura_handler.handler(event_2, None)
            
            # Assert 2: Second stamp should also SUCCEED
            assert response_2 is not None, "Response 2 should not be None"
            assert response_2['statusCode'] == HTTPStatus.OK, \
                f"Second stamp should succeed with 200, got {response_2['statusCode']}"
            
            response_2_body = json.loads(response_2['body'])
            uuid_2 = response_2_body.get('uuid')
            
            # Extract folio from second factura
            factura_2 = test_collections['facturas_emitidas'].find_one({'uuid': uuid_2})
            folio_2 = None
            if factura_2 and 'cfdi' in factura_2:
                import re
                folio_match = re.search(r'Folio="(\d+)"', factura_2['cfdi'])
                if folio_match:
                    folio_2 = folio_match.group(1)
            
            print(f"✅ Second stamp succeeded!")
            print(f"   UUID: {uuid_2}")
            print(f"   Folio: {folio_2}")
            
            # Get folio after second stamp
            folio_after_second = test_collections['folios'].find_one({"sucursal": test_sucursal})['noFolio']
            
            # Assertions
            
            # 1. Both UUIDs should be different
            assert uuid_1 != uuid_2, \
                f"UUIDs should be different. UUID1: {uuid_1}, UUID2: {uuid_2}"
            
            # 2. Folios should be consecutive
            assert folio_1 == str(initial_folio), \
                f"First folio should match initial. Expected: {initial_folio}, Got: {folio_1}"
            assert folio_2 == str(initial_folio + 1), \
                f"Second folio should be initial+1. Expected: {initial_folio + 1}, Got: {folio_2}"
            
            # 3. Folio counter should be incremented by 2
            assert folio_after_second == initial_folio + 2, \
                f"Final folio should be initial+2. Expected: {initial_folio + 2}, Got: {folio_after_second}"
            
            # 4. Both facturas should be saved
            assert factura_1 is not None, "First factura should be saved"
            assert factura_2 is not None, "Second factura should be saved"
            
            # 5. Tickets in DB should match (without hyphens in ticket_timbrado)
            ticket_1_db = test_collections['ticket_timbrado'].find_one({"ticket": test_ticket_1.replace("-", "")})
            ticket_2_db = test_collections['ticket_timbrado'].find_one({"ticket": test_ticket_2.replace("-", "")})
            assert ticket_1_db is not None, "First ticket should be in ticket_timbrado"
            assert ticket_2_db is not None, "Second ticket should be in ticket_timbrado"
            
            # 6. Both should have success entries in bitacora
            bitacora_1 = test_collections['bitacora'].find_one({
                "ticket": test_ticket_1,
                "status": "exito"
            })
            bitacora_2 = test_collections['bitacora'].find_one({
                "ticket": test_ticket_2,
                "status": "exito"
            })
            assert bitacora_1 is not None, "First ticket should have success bitacora entry"
            assert bitacora_2 is not None, "Second ticket should have success bitacora entry"
            
            # 7. Serie_folio entries should exist for both
            serie_folio_1 = test_collections['serie_folio'].find_one({
                "folioTimbrado": {"$regex": f".*{folio_1}"}
            })
            serie_folio_2 = test_collections['serie_folio'].find_one({
                "folioTimbrado": {"$regex": f".*{folio_2}"}
            })
            assert serie_folio_1 is not None, "Serie folio should exist for first ticket"
            assert serie_folio_2 is not None, "Serie folio should exist for second ticket"
            
            print(f"\n✅ Similar tickets test passed successfully!")
            print(f"   Initial folio: {initial_folio}")
            print(f"   Ticket 1: {test_ticket_1} → Folio: {folio_1} → UUID: {uuid_1[:8]}...")
            print(f"   Ticket 2: {test_ticket_2} → Folio: {folio_2} → UUID: {uuid_2[:8]}...")
            print(f"   Final folio: {folio_after_second}")
            print(f"   ✓ Both tickets stamped successfully")
            print(f"   ✓ Consecutive folios used")
            print(f"   ✓ No conflicts detected")
            
        finally:
            # Cleanup: Remove test data
            test_collections['ticket_timbrado'].delete_many({
                "ticket": {"$in": [test_ticket_1.replace("-", ""), test_ticket_2.replace("-", "")]}
            })
            test_collections['serie_folio'].delete_many({"folioTimbrado": {"$regex": f".*OSFI.*"}})
            test_collections['facturas_emitidas'].delete_many({
                "ticket": {"$in": [test_ticket_1, test_ticket_2]}
            })
            test_collections['bitacora'].delete_many({
                "ticket": {"$in": [test_ticket_1, test_ticket_2]}
            })

