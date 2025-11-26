"""
Integration tests for consumo_timbres_handler.
IMPORTANT: Environment variables must be loaded BEFORE importing any handlers.
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

# Now we can safely import modules that depend on environment variables
import pytest
import json
from http import HTTPStatus
from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime, timezone

# Import the actual handler (this will now work because env vars are loaded)
import invoice_cdk.lambdas.consumo_timbres_handler as consumo_timbres_handler


@pytest.fixture(scope='module')
def mongo_client():
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


@pytest.fixture(autouse=True)
def setup_teardown(test_db):
    """Setup and cleanup test data before/after each test"""
    # Setup: Clean collections before test
    test_db.certificates.delete_many({"usuario": {"$regex": "^test_consumo_"}})
    test_db.facturasemitidas.delete_many({"idCertificado": {"$regex": "^test_cert_"}})
    
    yield
    
    # Teardown: Clean after test
    test_db.certificates.delete_many({"usuario": {"$regex": "^test_consumo_"}})
    test_db.facturasemitidas.delete_many({"idCertificado": {"$regex": "^test_cert_"}})


@pytest.fixture
def sample_certificate_data():
    """Sample certificate data for testing"""
    return {
        "_id": "test_cert_001",
        "nombre": "Test Certificate Consumo",
        "rfc": "TESTCONSUMO123",
        "no_certificado": "30001000000400009999",
        "desde": datetime(2023, 1, 1),
        "hasta": datetime(2027, 12, 31),
        "sucursales": [],
        "usuario": "test_consumo_user@example.com"
    }


@pytest.fixture
def sample_factura_emitida_data():
    """Sample factura emitida data for testing"""
    return {
        "idCertificado": "test_cert_001",
        "folio": "A001",
        "serie": "A",
        "fechaTimbrado": datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        "total": 1000.00,
        "uuid": "12345678-1234-1234-1234-123456789012"
    }


class TestConsumoTimbresHandlerIntegrationGet:
    """Integration tests for GET method"""
    
    def test_get_consumo_timbres_real_db(self, sample_certificate_data, 
                                         sample_factura_emitida_data, test_db):
        """Test retrieving consumo timbres from real database"""
        # Insert test certificate
        test_db.certificates.insert_one(sample_certificate_data)
        
        # Insert test factura emitida
        test_db.facturasemitidas.insert_one(sample_factura_emitida_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_consumo_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) > 0
        assert "facturas_emitidas" in body[0]
        assert len(body[0]["facturas_emitidas"]) > 0
        assert body[0]["facturas_emitidas"][0]["folio"] == "A001"
    
    def test_get_consumo_timbres_no_certificates_real_db(self, test_db):
        """Test retrieving consumo timbres when user has no certificates"""
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_consumo_nonexistent@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) == 0
    
    def test_get_consumo_timbres_no_facturas_real_db(self, sample_certificate_data, test_db):
        """Test retrieving consumo timbres when certificate has no facturas"""
        # Insert test certificate but no facturas
        test_db.certificates.insert_one(sample_certificate_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_consumo_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) > 0
        assert body[0]["facturas_emitidas"] == []
    
    def test_get_consumo_timbres_date_range_filtering_real_db(self, sample_certificate_data,
                                                               sample_factura_emitida_data, test_db):
        """Test that date range filtering works correctly"""
        # Insert test certificate
        test_db.certificates.insert_one(sample_certificate_data)
        
        # Insert facturas with different dates
        factura1 = sample_factura_emitida_data.copy()
        factura1["fechaTimbrado"] = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        factura1["folio"] = "A001"
        
        factura2 = sample_factura_emitida_data.copy()
        factura2["fechaTimbrado"] = datetime(2024, 2, 15, 10, 30, 0, tzinfo=timezone.utc)
        factura2["folio"] = "A002"
        
        factura3 = sample_factura_emitida_data.copy()
        factura3["fechaTimbrado"] = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
        factura3["folio"] = "A003"
        
        test_db.facturasemitidas.insert_many([factura1, factura2, factura3])
        
        # Query only for January
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_consumo_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body[0]["facturas_emitidas"]) == 1
        assert body[0]["facturas_emitidas"][0]["folio"] == "A001"
    
    def test_get_consumo_timbres_multiple_certificates_real_db(self, sample_certificate_data,
                                                                sample_factura_emitida_data, test_db):
        """Test retrieving consumo timbres for multiple certificates"""
        # Insert two certificates
        cert1 = sample_certificate_data.copy()
        cert1["_id"] = "test_cert_001"
        test_db.certificates.insert_one(cert1)
        
        cert2 = sample_certificate_data.copy()
        cert2["_id"] = "test_cert_002"
        cert2["rfc"] = "TESTCONSUMO456"
        test_db.certificates.insert_one(cert2)
        
        # Insert facturas for both certificates
        factura1 = sample_factura_emitida_data.copy()
        factura1["idCertificado"] = "test_cert_001"
        factura1["folio"] = "A001"
        
        factura2 = sample_factura_emitida_data.copy()
        factura2["idCertificado"] = "test_cert_002"
        factura2["folio"] = "B001"
        
        test_db.facturasemitidas.insert_many([factura1, factura2])
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_consumo_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body) == 2
        # Each certificate should have its facturas
        folios = []
        for cert in body:
            for factura in cert["facturas_emitidas"]:
                folios.append(factura["folio"])
        assert "A001" in folios
        assert "B001" in folios


class TestConsumoTimbresHandlerIntegrationCORS:
    """Integration tests for CORS headers"""
    
    def test_cors_header_real_db(self, sample_certificate_data, test_db):
        """Test that CORS headers are properly set"""
        test_db.certificates.insert_one(sample_certificate_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_consumo_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        assert response["statusCode"] == 200
        assert "headers" in response
        assert "Access-Control-Allow-Origin" in response["headers"]
