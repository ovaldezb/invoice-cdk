"""
Unit tests for receptor_handler.
These tests use mocks and do not require a database connection.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from http import HTTPStatus
from bson import ObjectId


@pytest.fixture
def sample_receptor_data():
    """Sample receptor data for testing"""
    return {
        "_id": "TEST123456ABC",
        "Nombre": "Juan Perez",
        "DomicilioFiscalReceptor": "01000",
        "email": "juan@example.com",
        "Rfc": "TEST123456ABC",
        "RegimenFiscalReceptor": "601",
        "UsoCFDI": "G03"
    }


@pytest.fixture
def mock_receptor_model():
    """Mock Receptor model"""
    mock = MagicMock()
    mock.dict.return_value = {
        "_id": "TEST123456ABC",
        "Nombre": "Juan Perez",
        "DomicilioFiscalReceptor": "01000",
        "email": "juan@example.com",
        "Rfc": "TEST123456ABC",
        "RegimenFiscalReceptor": "601",
        "UsoCFDI": "G03"
    }
    return mock


class TestReceptorHandlerPost:
    """Unit tests for POST method (create receptor)"""
    
    @patch('invoice_cdk.lambdas.receptor_handler.guarda_receptor')
    @patch('invoice_cdk.lambdas.receptor_handler.Receptor')
    @patch('invoice_cdk.lambdas.receptor_handler.valida_cors')
    def test_create_receptor_success(self, mock_valida_cors, mock_receptor_class, 
                                     mock_guarda_receptor, sample_receptor_data):
        """Test successful receptor creation"""
        # Import handler after mocks are set up
        import invoice_cdk.lambdas.receptor_handler as receptor_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_receptor_instance = MagicMock()
        mock_receptor_class.return_value = mock_receptor_instance
        mock_guarda_receptor.return_value = ObjectId("507f1f77bcf86cd799439011")
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_receptor_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.CREATED
        assert "id" in json.loads(response["body"])
        mock_receptor_class.assert_called_once()
        mock_guarda_receptor.assert_called_once()
    
    @patch('invoice_cdk.lambdas.receptor_handler.Receptor')
    @patch('invoice_cdk.lambdas.receptor_handler.valida_cors')
    def test_create_receptor_invalid_data(self, mock_valida_cors, mock_receptor_class):
        """Test receptor creation with invalid data"""
        import invoice_cdk.lambdas.receptor_handler as receptor_handler
        
        # Setup mocks to raise validation error
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_receptor_class.side_effect = Exception("Validation error")
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({"invalid": "data"}),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        with pytest.raises(Exception):
            receptor_handler.handler(event, {})


class TestReceptorHandlerGet:
    """Unit tests for GET method (retrieve receptor)"""
    
    @patch('invoice_cdk.lambdas.receptor_handler.obtiene_receptor_by_rfc')
    @patch('invoice_cdk.lambdas.receptor_handler.valida_cors')
    def test_get_receptor_by_rfc_success(self, mock_valida_cors, mock_obtiene_receptor,
                                         sample_receptor_data):
        """Test successful receptor retrieval by RFC"""
        import invoice_cdk.lambdas.receptor_handler as receptor_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_obtiene_receptor.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "Nombre": "Juan Perez",
            "Rfc": "TEST123456ABC",
            "email": "juan@example.com"
        }
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id_receptor": "TEST123456ABC"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert "Nombre" in body
        mock_obtiene_receptor.assert_called_once_with("TEST123456ABC", receptor_handler.receptor_collection)
    
    @patch('invoice_cdk.lambdas.receptor_handler.obtiene_receptor_by_rfc')
    @patch('invoice_cdk.lambdas.receptor_handler.valida_cors')
    def test_get_receptor_not_found(self, mock_valida_cors, mock_obtiene_receptor):
        """Test receptor retrieval when receptor doesn't exist"""
        import invoice_cdk.lambdas.receptor_handler as receptor_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_obtiene_receptor.return_value = None
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id_receptor": "NONEXISTENT"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.NOT_FOUND
        body = json.loads(response["body"])
        assert "error" in body


class TestReceptorHandlerPut:
    """Unit tests for PUT method (update receptor)"""
    
    @patch('invoice_cdk.lambdas.receptor_handler.obtiene_receptor_by_rfc')
    @patch('invoice_cdk.lambdas.receptor_handler.update_receptor')
    @patch('invoice_cdk.lambdas.receptor_handler.valida_cors')
    def test_update_receptor_success(self, mock_valida_cors, mock_update_receptor,
                                     mock_obtiene_receptor, sample_receptor_data):
        """Test successful receptor update"""
        import invoice_cdk.lambdas.receptor_handler as receptor_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        
        # Mock UpdateResult with matched_count attribute
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_update_result.modified_count = 1
        mock_update_receptor.return_value = mock_update_result
        
        # Mock the updated receptor retrieval
        updated_receptor = sample_receptor_data.copy()
        updated_receptor["Nombre"] = "Juan Perez Updated"
        updated_receptor["_id"] = ObjectId("507f1f77bcf86cd799439011")
        mock_obtiene_receptor.return_value = updated_receptor
        
        updated_data = sample_receptor_data.copy()
        updated_data["Nombre"] = "Juan Perez Updated"
        
        event = {
            "httpMethod": "PUT",
            "pathParameters": {"id_receptor": "TEST123456ABC"},
            "body": json.dumps(updated_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert "message" in body
        assert body["message"] == "Receptor updated"
        mock_update_receptor.assert_called_once()
        mock_obtiene_receptor.assert_called_once()


class TestReceptorHandlerInvalidMethod:
    """Unit tests for invalid HTTP methods"""
    
    @patch('invoice_cdk.lambdas.receptor_handler.valida_cors')
    def test_invalid_method(self, mock_valida_cors):
        """Test handler with invalid HTTP method"""
        import invoice_cdk.lambdas.receptor_handler as receptor_handler
        
        mock_valida_cors.return_value = "http://localhost:3000"
        
        event = {
            "httpMethod": "DELETE",  # Not supported
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = receptor_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.BAD_REQUEST
        body = json.loads(response["body"])
        assert "error" in body
