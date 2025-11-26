"""
Integration tests for datos_factura_handler.
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
import invoice_cdk.lambdas.datos_factura_handler as datos_factura_handler


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
    test_db.usocfdis.delete_many({})
    test_db.regimenfiscal.delete_many({})
    test_db.formapago.delete_many({})
    
    yield
    
    # Teardown: Clean after test
    test_db.usocfdis.delete_many({})
    test_db.regimenfiscal.delete_many({})
    test_db.formapago.delete_many({})


@pytest.fixture
def sample_test_data(test_db):
    """Insert sample test data into all collections"""
    # Insert uso CFDI data
    uso_cfdi_data = [
        {"clave": "G01", "descripcion": "Adquisición de mercancías"},
        {"clave": "G03", "descripcion": "Gastos en general"},
        {"clave": "I01", "descripcion": "Construcciones"}
    ]
    test_db.usocfdis.insert_many(uso_cfdi_data)
    
    # Insert regimen fiscal data
    regimen_fiscal_data = [
        {"clave": "601", "descripcion": "General de Ley Personas Morales"},
        {"clave": "612", "descripcion": "Personas Físicas con Actividades Empresariales"},
        {"clave": "626", "descripcion": "Régimen Simplificado de Confianza"}
    ]
    test_db.regimenfiscal.insert_many(regimen_fiscal_data)
    
    # Insert forma pago data
    forma_pago_data = [
        {"clave": "01", "descripcion": "Efectivo"},
        {"clave": "03", "descripcion": "Transferencia electrónica de fondos"},
        {"clave": "04", "descripcion": "Tarjeta de crédito"}
    ]
    test_db.formapago.insert_many(forma_pago_data)
    
    return {
        "uso_cfdi": uso_cfdi_data,
        "regimen_fiscal": regimen_fiscal_data,
        "forma_pago": forma_pago_data
    }


class TestDatosFacturaHandlerIntegrationGet:
    """Integration tests for GET method"""
    
    def test_get_all_datos_factura_real_db(self, sample_test_data, test_db):
        """Test retrieving all datos factura from real database"""
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        
        # Verify all keys exist
        assert "uso_cfdi" in body
        assert "regimen_fiscal" in body
        assert "forma_pago" in body
        
        # Verify counts
        assert len(body["uso_cfdi"]) == 3
        assert len(body["regimen_fiscal"]) == 3
        assert len(body["forma_pago"]) == 3
        
        # Verify structure of uso_cfdi
        assert body["uso_cfdi"][0]["clave"] in ["G01", "G03", "I01"]
        assert "descripcion" in body["uso_cfdi"][0]
        assert "_id" in body["uso_cfdi"][0]
        assert isinstance(body["uso_cfdi"][0]["_id"], str)
        
        # Verify structure of regimen_fiscal
        assert body["regimen_fiscal"][0]["clave"] in ["601", "612", "626"]
        assert "descripcion" in body["regimen_fiscal"][0]
        assert "_id" in body["regimen_fiscal"][0]
        assert isinstance(body["regimen_fiscal"][0]["_id"], str)
        
        # Verify structure of forma_pago
        assert body["forma_pago"][0]["clave"] in ["01", "03", "04"]
        assert "descripcion" in body["forma_pago"][0]
        assert "_id" in body["forma_pago"][0]
        assert isinstance(body["forma_pago"][0]["_id"], str)
    
    def test_get_datos_factura_empty_collections_real_db(self, test_db):
        """Test retrieving from empty collections"""
        # Collections are already empty due to setup_teardown
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        
        # Verify all are empty lists
        assert body["uso_cfdi"] == []
        assert body["regimen_fiscal"] == []
        assert body["forma_pago"] == []
    
    def test_get_datos_factura_specific_data_real_db(self, test_db):
        """Test retrieving specific known data"""
        # Insert specific test data
        test_db.usocfdis.insert_one({"clave": "G01", "descripcion": "Adquisición de mercancías"})
        test_db.regimenfiscal.insert_one({"clave": "601", "descripcion": "General de Ley Personas Morales"})
        test_db.formapago.insert_one({"clave": "01", "descripcion": "Efectivo"})
        
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        
        # Verify specific data
        assert len(body["uso_cfdi"]) == 1
        assert body["uso_cfdi"][0]["clave"] == "G01"
        assert body["uso_cfdi"][0]["descripcion"] == "Adquisición de mercancías"
        
        assert len(body["regimen_fiscal"]) == 1
        assert body["regimen_fiscal"][0]["clave"] == "601"
        assert body["regimen_fiscal"][0]["descripcion"] == "General de Ley Personas Morales"
        
        assert len(body["forma_pago"]) == 1
        assert body["forma_pago"][0]["clave"] == "01"
        assert body["forma_pago"][0]["descripcion"] == "Efectivo"
    
    def test_cors_header_real_db(self, sample_test_data, test_db):
        """Test that CORS headers are properly set"""
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:4200"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        assert "headers" in response
        assert "Access-Control-Allow-Origin" in response["headers"]


class TestDatosFacturaHandlerIntegrationInvalidMethod:
    """Integration tests for invalid methods"""
    
    def test_post_method_not_supported_real_db(self, test_db):
        """Test that POST method is not supported"""
        event = {
            "httpMethod": "POST",
            "headers": {"origin": "http://localhost:3000"},
            "body": json.dumps({"test": "data"})
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Handler doesn't implement POST, so it returns None
        assert response is None
    
    def test_put_method_not_supported_real_db(self, test_db):
        """Test that PUT method is not supported"""
        event = {
            "httpMethod": "PUT",
            "headers": {"origin": "http://localhost:3000"},
            "body": json.dumps({"test": "data"})
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Handler doesn't implement PUT, so it returns None
        assert response is None
