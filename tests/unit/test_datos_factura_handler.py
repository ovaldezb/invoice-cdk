"""
Unit tests for datos_factura_handler.
These tests use mocks and do not require a database connection.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from http import HTTPStatus
from bson import ObjectId


@pytest.fixture
def sample_uso_cfdi_data():
    """Sample uso CFDI data for testing"""
    return [
        {"_id": ObjectId("507f1f77bcf86cd799439011"), "clave": "G01", "descripcion": "Adquisición de mercancías"},
        {"_id": ObjectId("507f1f77bcf86cd799439012"), "clave": "G03", "descripcion": "Gastos en general"}
    ]


@pytest.fixture
def sample_regimen_fiscal_data():
    """Sample regimen fiscal data for testing"""
    return [
        {"_id": ObjectId("507f1f77bcf86cd799439013"), "clave": "601", "descripcion": "General de Ley Personas Morales"},
        {"_id": ObjectId("507f1f77bcf86cd799439014"), "clave": "612", "descripcion": "Personas Físicas con Actividades Empresariales"}
    ]


@pytest.fixture
def sample_forma_pago_data():
    """Sample forma pago data for testing"""
    return [
        {"_id": ObjectId("507f1f77bcf86cd799439015"), "clave": "01", "descripcion": "Efectivo"},
        {"_id": ObjectId("507f1f77bcf86cd799439016"), "clave": "03", "descripcion": "Transferencia electrónica de fondos"}
    ]


class TestDatosFacturaHandlerGet:
    """Unit tests for GET method (retrieve all datos factura)"""
    
    @patch('invoice_cdk.lambdas.datos_factura_handler.get_forma_pago')
    @patch('invoice_cdk.lambdas.datos_factura_handler.get_regimen_fiscal')
    @patch('invoice_cdk.lambdas.datos_factura_handler.get_uso_cfdi')
    @patch('invoice_cdk.lambdas.datos_factura_handler.valida_cors')
    def test_get_datos_factura_success(self, mock_valida_cors, mock_get_uso_cfdi,
                                       mock_get_regimen_fiscal, mock_get_forma_pago,
                                       sample_uso_cfdi_data, sample_regimen_fiscal_data,
                                       sample_forma_pago_data):
        """Test successful retrieval of all datos factura"""
        import invoice_cdk.lambdas.datos_factura_handler as datos_factura_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_get_uso_cfdi.return_value = sample_uso_cfdi_data.copy()
        mock_get_regimen_fiscal.return_value = sample_regimen_fiscal_data.copy()
        mock_get_forma_pago.return_value = sample_forma_pago_data.copy()
        
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert "uso_cfdi" in body
        assert "regimen_fiscal" in body
        assert "forma_pago" in body
        assert len(body["uso_cfdi"]) == 2
        assert len(body["regimen_fiscal"]) == 2
        assert len(body["forma_pago"]) == 2
        
        # Verify ObjectIds were converted to strings
        assert isinstance(body["uso_cfdi"][0]["_id"], str)
        assert isinstance(body["regimen_fiscal"][0]["_id"], str)
        assert isinstance(body["forma_pago"][0]["_id"], str)
        
        # Verify function calls
        mock_get_uso_cfdi.assert_called_once()
        mock_get_regimen_fiscal.assert_called_once()
        mock_get_forma_pago.assert_called_once()
    
    @patch('invoice_cdk.lambdas.datos_factura_handler.get_forma_pago')
    @patch('invoice_cdk.lambdas.datos_factura_handler.get_regimen_fiscal')
    @patch('invoice_cdk.lambdas.datos_factura_handler.get_uso_cfdi')
    @patch('invoice_cdk.lambdas.datos_factura_handler.valida_cors')
    def test_get_datos_factura_empty_collections(self, mock_valida_cors, mock_get_uso_cfdi,
                                                  mock_get_regimen_fiscal, mock_get_forma_pago):
        """Test retrieval when collections are empty"""
        import invoice_cdk.lambdas.datos_factura_handler as datos_factura_handler
        
        # Setup mocks with empty lists
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_get_uso_cfdi.return_value = []
        mock_get_regimen_fiscal.return_value = []
        mock_get_forma_pago.return_value = []
        
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["uso_cfdi"] == []
        assert body["regimen_fiscal"] == []
        assert body["forma_pago"] == []
    
    @patch('invoice_cdk.lambdas.datos_factura_handler.get_uso_cfdi')
    @patch('invoice_cdk.lambdas.datos_factura_handler.valida_cors')
    def test_get_datos_factura_exception_handling(self, mock_valida_cors, mock_get_uso_cfdi):
        """Test exception handling in GET method"""
        import invoice_cdk.lambdas.datos_factura_handler as datos_factura_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_get_uso_cfdi.side_effect = Exception("Database connection error")
        
        event = {
            "httpMethod": "GET",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.INTERNAL_SERVER_ERROR
        body = json.loads(response["body"])
        assert "error" in body
        assert "Database connection error" in body["error"]


class TestDatosFacturaHandlerInvalidMethod:
    """Unit tests for invalid HTTP methods"""
    
    @patch('invoice_cdk.lambdas.datos_factura_handler.valida_cors')
    def test_post_method_not_supported(self, mock_valida_cors):
        """Test that POST method returns None (not implemented)"""
        import invoice_cdk.lambdas.datos_factura_handler as datos_factura_handler
        
        mock_valida_cors.return_value = "http://localhost:3000"
        
        event = {
            "httpMethod": "POST",
            "headers": {"origin": "http://localhost:3000"},
            "body": json.dumps({"test": "data"})
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Handler doesn't have POST implemented, so it returns None
        assert response is None
    
    @patch('invoice_cdk.lambdas.datos_factura_handler.valida_cors')
    def test_put_method_not_supported(self, mock_valida_cors):
        """Test that PUT method returns None (not implemented)"""
        import invoice_cdk.lambdas.datos_factura_handler as datos_factura_handler
        
        mock_valida_cors.return_value = "http://localhost:3000"
        
        event = {
            "httpMethod": "PUT",
            "headers": {"origin": "http://localhost:3000"},
            "body": json.dumps({"test": "data"})
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Handler doesn't have PUT implemented, so it returns None
        assert response is None
    
    @patch('invoice_cdk.lambdas.datos_factura_handler.valida_cors')
    def test_delete_method_not_supported(self, mock_valida_cors):
        """Test that DELETE method returns None (not implemented)"""
        import invoice_cdk.lambdas.datos_factura_handler as datos_factura_handler
        
        mock_valida_cors.return_value = "http://localhost:3000"
        
        event = {
            "httpMethod": "DELETE",
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = datos_factura_handler.handler(event, {})
        
        # Handler doesn't have DELETE implemented, so it returns None
        assert response is None
