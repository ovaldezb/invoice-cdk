"""
Integration tests for receptor_handler.
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

# Import the actual handler (this will now work because env vars are loaded)
import invoice_cdk.lambdas.receptor_handler as receptor_handler


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
    test_db.receptors.delete_many({})
    
    yield
    
    # Teardown: Clean after test
    test_db.receptors.delete_many({})


@pytest.fixture
def sample_receptor_data():
    """Sample receptor data for testing"""
    return {
        "_id": "TEST123456ABC",
        "Nombre": "Juan Perez Test",
        "DomicilioFiscalReceptor": "01000",
        "email": "juan.test@example.com",
        "Rfc": "TEST123456ABC",
        "RegimenFiscalReceptor": "601",
        "UsoCFDI": "G03"
    }


class TestReceptorHandlerIntegrationPost:
    """Integration tests for POST method"""
    
    def test_create_receptor_real_db(self, sample_receptor_data, test_db):
        """Test creating receptor with real database"""
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_receptor_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.CREATED
        body = json.loads(response["body"])
        assert "id" in body
        
        # Verify in database
        receptor = test_db.receptors.find_one({"Rfc": "TEST123456ABC"})
        assert receptor is not None
        assert receptor["Nombre"] == "Juan Perez Test"
        assert receptor["email"] == "juan.test@example.com"


class TestReceptorHandlerIntegrationGet:
    """Integration tests for GET method"""
    
    def test_get_receptor_real_db(self, sample_receptor_data, test_db):
        """Test retrieving receptor from real database"""
        # Insert test data
        test_db.receptors.insert_one(sample_receptor_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id_receptor": "TEST123456ABC"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["Rfc"] == "TEST123456ABC"
        assert body["Nombre"] == "Juan Perez Test"
    
    def test_get_receptor_not_found_real_db(self, test_db):
        """Test retrieving non-existent receptor from real database"""
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id_receptor": "NONEXISTENT123"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.NOT_FOUND
        body = json.loads(response["body"])
        assert "error" in body


class TestReceptorHandlerIntegrationPut:
    """Integration tests for PUT method"""
    
    def test_update_receptor_real_db(self, sample_receptor_data, test_db):
        """Test updating receptor in real database"""
        # Insert test data
        test_db.receptors.insert_one(sample_receptor_data)
        
        # Create updated data
        updated_data = sample_receptor_data.copy()
        updated_data["Nombre"] = "Juan Perez Updated"
        updated_data["email"] = "juan.updated@example.com"
        
        event = {
            "httpMethod": "PUT",
            "pathParameters": {"id_receptor": "TEST123456ABC"},
            "body": json.dumps(updated_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        
        # Verify in database
        receptor = test_db.receptors.find_one({"Rfc": "TEST123456ABC"})
        assert receptor["Nombre"] == "Juan Perez Updated"
        assert receptor["email"] == "juan.updated@example.com"


class TestReceptorHandlerIntegrationInvalidMethod:
    """Integration tests for invalid methods"""
    
    def test_invalid_http_method_real_db(self, test_db):
        """Test handler with invalid HTTP method"""
        event = {
            "httpMethod": "DELETE",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.BAD_REQUEST
        body = json.loads(response["body"])
        assert "error" in body
