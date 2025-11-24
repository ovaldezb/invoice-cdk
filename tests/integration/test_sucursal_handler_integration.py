"""
Integration tests for sucursal_handler.
IMPORTANT: Environment variables must be loaded BEFORE importing any handlers.
"""
import os
from pathlib import Path

# Load environment variables BEFORE any other imports
env_file = Path(__file__).parent.parent.parent / '.env_dev'
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
    raise FileNotFoundError(f"Required .env_dev file not found at {env_file}")

# Now we can safely import modules that depend on environment variables
import pytest
import json
from http import HTTPStatus
from bson import ObjectId
from pymongo import MongoClient

# Import the actual handler (this will now work because env vars are loaded)
import invoice_cdk.lambdas.sucursal_handler as sucursal_handler


@pytest.fixture(scope='module')
def mongo_client():
    """Create MongoDB client for testing"""
    # Use the same database configuration as the handler
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
    test_db.sucursales.delete_many({})
    test_db.certificates.delete_many({})  # Changed from 'certificados' to match handler
    test_db.folios.delete_many({})
    
    yield
    
    # Teardown: Clean after test
    test_db.sucursales.delete_many({})
    test_db.certificates.delete_many({})  # Changed from 'certificados' to match handler
    test_db.folios.delete_many({})


@pytest.fixture
def certificado_id(test_db):
    """Create a test certificate"""
    cert = {
        "nombre": "Test Certificate",
        "rfc": "TEST123456",
        "sucursales": []
    }
    result = test_db.certificates.insert_one(cert)  # Changed from 'certificados' to match handler
    return str(result.inserted_id)


@pytest.fixture
def sample_sucursal_data(certificado_id):
    """Sample sucursal data for testing"""
    return {
        "codigo_sucursal": "378",
        "serie": "OPI",
        "direccion": "Vialidad de la Barranca 6 PB 27",
        "codigo_postal": "52787",
        "responsable": "Cesar Esquivel",
        "telefono": "5544889270",
        "regimen_fiscal": "601",
        "folio": "1",
        "id_certificado": certificado_id
    }


class TestSucursalHandlerIntegrationPost:
    """Integration tests for POST method"""
    
    def test_create_sucursal_real_db(self, sample_sucursal_data, test_db):
        """Test creating sucursal with real database"""
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_sucursal_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.CREATED
        body = json.loads(response["body"])
        assert "id" in body
        
        # Verify in database
        sucursal = test_db.sucursales.find_one({"_id": ObjectId(body["id"])})
        assert sucursal is not None
        assert sucursal["codigo_sucursal"] == "378"
        assert sucursal["serie"] == "OPI"


class TestSucursalHandlerIntegrationGet:
    """Integration tests for GET method"""
    
    def test_get_sucursal_real_db(self, sample_sucursal_data, test_db):
        """Test retrieving sucursal from real database"""
        # Insert test data
        result = test_db.sucursales.insert_one(sample_sucursal_data)
        sucursal_id = str(result.inserted_id)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": sample_sucursal_data["codigo_sucursal"]},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["codigo_sucursal"] == "378"
    
    def test_get_all_sucursales_real_db(self, sample_sucursal_data, test_db):
        """Test retrieving all sucursales from real database"""
        # Insert multiple test records
        test_db.sucursales.insert_many([
            sample_sucursal_data,
            {**sample_sucursal_data, "codigo_sucursal": "379", "serie": "OPI2"}
        ])
        
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert len(body) >= 2


class TestSucursalHandlerIntegrationPut:
    """Integration tests for PUT method"""
    
    def test_update_sucursal_real_db(self, sample_sucursal_data, test_db):
        """Test updating sucursal in real database"""
        # Insert test data
        result = test_db.sucursales.insert_one(sample_sucursal_data)
        sucursal_id = str(result.inserted_id)
        
        # Create updated data without the _id field (handler removes it anyway)
        updated_data = sample_sucursal_data.copy()
        updated_data["responsable"] = "Juan Perez"
        updated_data["_id"] = sucursal_id  # Add _id as string for handler to remove
        
        event = {
            "httpMethod": "PUT",
            "pathParameters": {"id": sucursal_id},
            "body": json.dumps(updated_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        
        # Verify in database
        sucursal = test_db.sucursales.find_one({"_id": ObjectId(sucursal_id)})
        assert sucursal["responsable"] == "Juan Perez"


class TestSucursalHandlerIntegrationDelete:
    """Integration tests for DELETE method"""
    
    def test_delete_sucursal_real_db(self, sample_sucursal_data, certificado_id, test_db):
        """Test deleting sucursal from real database"""
        # Insert test data
        result = test_db.sucursales.insert_one(sample_sucursal_data)
        sucursal_id = str(result.inserted_id)
        
        # Update certificate with sucursal reference (use 'certificates' to match handler)
        test_db.certificates.update_one(
            {"_id": ObjectId(certificado_id)},
            {"$push": {"sucursales": {"_id": sucursal_id, "codigo": "378"}}}
        )
        
        event = {
            "httpMethod": "DELETE",
            "pathParameters": {"id": sucursal_id},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        
        # Verify deletion
        sucursal = test_db.sucursales.find_one({"_id": ObjectId(sucursal_id)})
        assert sucursal is None
