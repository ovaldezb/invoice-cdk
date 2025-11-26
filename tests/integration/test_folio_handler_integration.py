"""
Integration tests for folio_handler.
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
import invoice_cdk.lambdas.folio_handler as folio_handler


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
    test_db.folios.delete_many({"sucursal": {"$regex": "^TEST_"}})
    
    yield
    
    # Teardown: Clean after test
    test_db.folios.delete_many({"sucursal": {"$regex": "^TEST_"}})


@pytest.fixture
def sample_folio_data():
    """Sample folio data for testing"""
    return {
        "_id": "test_folio_001",
        "sucursal": "TEST_SUC001",
        "noFolio": 1
    }


class TestFolioHandlerIntegrationPost:
    """Integration tests for POST method"""
    
    def test_create_folio_real_db(self, sample_folio_data, test_db):
        """Test creating folio with real database"""
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_folio_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.CREATED
        body = json.loads(response["body"])
        assert "id_folio" in body
        
        # Verify in database
        folio = test_db.folios.find_one({"sucursal": "TEST_SUC001"})
        assert folio is not None
        assert folio["sucursal"] == "TEST_SUC001"
        assert folio["noFolio"] == 1
    
    def test_create_folio_already_exists_real_db(self, sample_folio_data, test_db):
        """Test creating folio when it already exists"""
        # Insert test folio first
        test_db.folios.insert_one(sample_folio_data)
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_folio_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.ACCEPTED
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio already exists"
        
        # Verify only one folio exists
        folio_count = test_db.folios.count_documents({"sucursal": "TEST_SUC001"})
        assert folio_count == 1


class TestFolioHandlerIntegrationGet:
    """Integration tests for GET method"""
    
    def test_get_folio_by_sucursal_real_db(self, sample_folio_data, test_db):
        """Test retrieving folio from real database"""
        # Insert test folio
        test_db.folios.insert_one(sample_folio_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"sucursal": "TEST_SUC001"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert "folio" in body
        assert body["folio"]["sucursal"] == "TEST_SUC001"
        assert body["folio"]["noFolio"] == 1
    
    def test_get_folio_not_found_real_db(self, test_db):
        """Test retrieving non-existent folio from real database"""
        event = {
            "httpMethod": "GET",
            "pathParameters": {"sucursal": "TEST_NONEXISTENT"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.NOT_FOUND
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio not found"


class TestFolioHandlerIntegrationPut:
    """Integration tests for PUT method"""
    
    def test_update_folio_real_db(self, sample_folio_data, test_db):
        """Test updating folio in real database"""
        # Insert test folio
        test_db.folios.insert_one(sample_folio_data)
        
        # Update folio
        update_data = {
            "codigo_sucursal": "TEST_SUC001",
            "folio": 100
        }
        
        event = {
            "httpMethod": "PUT",
            "body": json.dumps(update_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio updated"
        
        # Verify in database
        folio = test_db.folios.find_one({"sucursal": "TEST_SUC001"})
        assert folio["noFolio"] == 100
    
    def test_update_folio_not_found_real_db(self, test_db):
        """Test updating non-existent folio"""
        update_data = {
            "codigo_sucursal": "TEST_NONEXISTENT",
            "folio": 100
        }
        
        event = {
            "httpMethod": "PUT",
            "body": json.dumps(update_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.NOT_FOUND
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio not found"


class TestFolioHandlerIntegrationCORS:
    """Integration tests for CORS headers"""
    
    def test_cors_header_real_db(self, sample_folio_data, test_db):
        """Test that CORS headers are properly set"""
        # Insert test folio
        test_db.folios.insert_one(sample_folio_data)
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"sucursal": "TEST_SUC001"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        assert "headers" in response
        assert "Access-Control-Allow-Origin" in response["headers"]
