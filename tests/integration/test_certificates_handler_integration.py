"""
Integration tests for certificates_handler.
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
from datetime import datetime

# Import the actual handler (this will now work because env vars are loaded)
import invoice_cdk.lambdas.certificates_handler as certificates_handler


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
    test_db.certificates.delete_many({"usuario": {"$regex": "^test_"}})
    test_db.sucursales.delete_many({"codigo_sucursal": {"$regex": "^TEST_"}})
    test_db.folios.delete_many({"sucursal": {"$regex": "^TEST_"}})
    
    yield
    
    # Teardown: Clean after test
    test_db.certificates.delete_many({"usuario": {"$regex": "^test_"}})
    test_db.sucursales.delete_many({"codigo_sucursal": {"$regex": "^TEST_"}})
    test_db.folios.delete_many({"sucursal": {"$regex": "^TEST_"}})


@pytest.fixture
def sample_certificate_data():
    """Sample certificate data for testing"""
    return {
        "nombre": "Test Certificate Integration",
        "rfc": "TEST123456ABC",
        "no_certificado": "30001000000400002345",
        "desde": "2023-01-01T00:00:00",
        "hasta": "2027-12-31T23:59:59",
        "sucursales": [],
        "usuario": "test_user_integration@example.com"
    }


@pytest.fixture
def sample_sucursal_data():
    """Sample sucursal data for testing"""
    return {
        "codigo_sucursal": "TEST_SUC001",
        "nombre": "Sucursal Test Integration",
        "direccion": "Test Address"
    }


class TestCertificatesHandlerIntegrationPost:
    """Integration tests for POST method"""
    
    def test_create_certificate_real_db(self, sample_certificate_data, test_db):
        """Test creating certificate with real database"""
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_certificate_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.CREATED
        body = json.loads(response["body"])
        assert "id" in body
        assert body["message"] == "Certificate added"
        
        # Verify in database
        certificate = test_db.certificates.find_one({
            "usuario": "test_user_integration@example.com"
        })
        assert certificate is not None
        assert certificate["nombre"] == "Test Certificate Integration"
        assert certificate["rfc"] == "TEST123456ABC"
        assert certificate["no_certificado"] == "30001000000400002345"


class TestCertificatesHandlerIntegrationGet:
    """Integration tests for GET method"""
    
    def test_get_certificates_by_usuario_real_db(self, sample_certificate_data, test_db):
        """Test retrieving certificates from real database"""
        # Insert test certificate
        cert_data = sample_certificate_data.copy()
        cert_data["desde"] = datetime.fromisoformat(cert_data["desde"])
        cert_data["hasta"] = datetime.fromisoformat(cert_data["hasta"])
        test_db.certificates.insert_one(cert_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "test_user_integration@example.com"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) > 0
        assert body[0]["nombre"] == "Test Certificate Integration"
        assert body[0]["rfc"] == "TEST123456ABC"
    
    def test_get_certificates_with_sucursales_real_db(self, sample_certificate_data,
                                                      sample_sucursal_data, test_db):
        """Test retrieving certificates with associated sucursales"""
        # Insert test sucursal
        sucursal_result = test_db.sucursales.insert_one(sample_sucursal_data)
        sucursal_id = sucursal_result.inserted_id
        
        # Insert test certificate with sucursal reference
        cert_data = sample_certificate_data.copy()
        cert_data["desde"] = datetime.fromisoformat(cert_data["desde"])
        cert_data["hasta"] = datetime.fromisoformat(cert_data["hasta"])
        cert_data["sucursales"] = [{"_id": sucursal_id}]
        test_db.certificates.insert_one(cert_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "test_user_integration@example.com"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert len(body) > 0
        assert len(body[0]["sucursales"]) > 0
        assert body[0]["sucursales"][0]["codigo_sucursal"] == "TEST_SUC001"
    
    def test_get_certificates_empty_result_real_db(self, test_db):
        """Test retrieving certificates when none exist for usuario"""
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "test_nonexistent_user@example.com"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) == 0


class TestCertificatesHandlerIntegrationPut:
    """Integration tests for PUT method"""
    
    def test_update_certificate_real_db(self, sample_certificate_data, test_db):
        """Test updating certificate in real database"""
        # Insert test certificate
        cert_data = sample_certificate_data.copy()
        cert_data["desde"] = datetime.fromisoformat(cert_data["desde"])
        cert_data["hasta"] = datetime.fromisoformat(cert_data["hasta"])
        result = test_db.certificates.insert_one(cert_data)
        cert_id = str(result.inserted_id)
        
        # Create updated data
        updated_data = sample_certificate_data.copy()
        updated_data["_id"] = cert_id
        updated_data["nombre"] = "Updated Certificate Name"
        updated_data["rfc"] = "UPDATED123ABC"
        
        event = {
            "httpMethod": "PUT",
            "pathParameters": {"id": cert_id},
            "body": json.dumps(updated_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Certificate updated"
        
        # Verify in database
        certificate = test_db.certificates.find_one({"_id": ObjectId(cert_id)})
        assert certificate["nombre"] == "Updated Certificate Name"
        assert certificate["rfc"] == "UPDATED123ABC"


class TestCertificatesHandlerIntegrationDelete:
    """Integration tests for DELETE method"""
    
    def test_delete_certificate_with_sucursales_real_db(self, sample_certificate_data,
                                                        sample_sucursal_data, test_db):
        """Test deleting certificate with associated sucursales"""
        # Insert test sucursal
        sucursal_result = test_db.sucursales.insert_one(sample_sucursal_data)
        sucursal_id = sucursal_result.inserted_id
        
        # Insert test folio for the sucursal
        test_db.folios.insert_one({
            "sucursal": "TEST_SUC001",
            "folio": "A001"
        })
        
        # Insert test certificate with sucursal reference
        cert_data = sample_certificate_data.copy()
        cert_data["desde"] = datetime.fromisoformat(cert_data["desde"])
        cert_data["hasta"] = datetime.fromisoformat(cert_data["hasta"])
        cert_data["sucursales"] = [{"_id": sucursal_id, "codigo_sucursal": "TEST_SUC001"}]
        cert_result = test_db.certificates.insert_one(cert_data)
        cert_id = str(cert_result.inserted_id)
        
        event = {
            "httpMethod": "DELETE",
            "pathParameters": {"id": cert_id},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Certificate deleted"
        
        # Verify certificate is deleted
        certificate = test_db.certificates.find_one({"_id": ObjectId(cert_id)})
        assert certificate is None
        
        # Verify sucursal is deleted
        sucursal = test_db.sucursales.find_one({"_id": sucursal_id})
        assert sucursal is None
        
        # Verify folio is deleted
        folio = test_db.folios.find_one({"sucursal": "TEST_SUC001"})
        assert folio is None
    
    def test_delete_certificate_without_sucursales_real_db(self, sample_certificate_data, test_db):
        """Test deleting certificate without sucursales"""
        # Insert test certificate without sucursales
        cert_data = sample_certificate_data.copy()
        cert_data["desde"] = datetime.fromisoformat(cert_data["desde"])
        cert_data["hasta"] = datetime.fromisoformat(cert_data["hasta"])
        result = test_db.certificates.insert_one(cert_data)
        cert_id = str(result.inserted_id)
        
        event = {
            "httpMethod": "DELETE",
            "pathParameters": {"id": cert_id},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Certificate deleted"
        
        # Verify certificate is deleted
        certificate = test_db.certificates.find_one({"_id": ObjectId(cert_id)})
        assert certificate is None
