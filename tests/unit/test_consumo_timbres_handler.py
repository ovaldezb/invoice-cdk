"""
Unit tests for consumo_timbres_handler.
These tests use mocks and do not require a database connection.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from http import HTTPStatus
from bson import ObjectId
from datetime import datetime, timezone


@pytest.fixture
def sample_certificate_data():
    """Sample certificate data for testing"""
    return {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "nombre": "Test Certificate",
        "rfc": "TEST123456ABC",
        "no_certificado": "30001000000400002345",
        "usuario": "test_user@example.com"
    }


@pytest.fixture
def sample_factura_emitida_data():
    """Sample factura emitida data for testing"""
    return {
        "_id": ObjectId("507f1f77bcf86cd799439012"),
        "idCertificado": "507f1f77bcf86cd799439011",
        "folio": "A001",
        "serie": "A",
        "fechaTimbrado": datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        "total": 1000.00
    }


class TestConsumoTimbresHandlerGet:
    """Unit tests for GET method (retrieve consumo timbres)"""
    
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.consulta_facturas_emitidas_by_certificado')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.list_certificates')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.valida_cors')
    def test_get_consumo_timbres_success(self, mock_valida_cors, mock_list_certificates,
                                         mock_consulta_facturas, sample_certificate_data,
                                         sample_factura_emitida_data):
        """Test successful retrieval of consumo timbres"""
        import invoice_cdk.lambdas.consumo_timbres_handler as consumo_timbres_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_list_certificates.return_value = [sample_certificate_data.copy()]
        mock_consulta_facturas.return_value = [sample_factura_emitida_data.copy()]
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) > 0
        assert "facturas_emitidas" in body[0]
        mock_list_certificates.assert_called_once_with(
            "test_user@example.com",
            consumo_timbres_handler.certificates_collection
        )
        mock_consulta_facturas.assert_called_once()
    
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.consulta_facturas_emitidas_by_certificado')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.list_certificates')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.valida_cors')
    def test_get_consumo_timbres_no_certificates(self, mock_valida_cors, mock_list_certificates,
                                                  mock_consulta_facturas):
        """Test retrieval when user has no certificates"""
        import invoice_cdk.lambdas.consumo_timbres_handler as consumo_timbres_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_list_certificates.return_value = []
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "user_without_certs@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) == 0
        mock_consulta_facturas.assert_not_called()
    
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.consulta_facturas_emitidas_by_certificado')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.list_certificates')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.valida_cors')
    def test_get_consumo_timbres_no_facturas(self, mock_valida_cors, mock_list_certificates,
                                             mock_consulta_facturas, sample_certificate_data):
        """Test retrieval when certificate has no facturas emitidas"""
        import invoice_cdk.lambdas.consumo_timbres_handler as consumo_timbres_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_list_certificates.return_value = [sample_certificate_data.copy()]
        mock_consulta_facturas.return_value = []
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) > 0
        assert body[0]["facturas_emitidas"] == []
    
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.consulta_facturas_emitidas_by_certificado')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.list_certificates')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.valida_cors')
    def test_get_consumo_timbres_multiple_certificates(self, mock_valida_cors, mock_list_certificates,
                                                       mock_consulta_facturas, sample_certificate_data,
                                                       sample_factura_emitida_data):
        """Test retrieval with multiple certificates"""
        import invoice_cdk.lambdas.consumo_timbres_handler as consumo_timbres_handler
        
        # Setup mocks - two certificates
        cert1 = sample_certificate_data.copy()
        cert2 = sample_certificate_data.copy()
        cert2["_id"] = ObjectId("507f1f77bcf86cd799439099")
        cert2["rfc"] = "TEST987654XYZ"
        
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_list_certificates.return_value = [cert1, cert2]
        mock_consulta_facturas.return_value = [sample_factura_emitida_data.copy()]
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        # Assertions
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) == 2
        assert mock_consulta_facturas.call_count == 2


class TestConsumoTimbresHandlerExceptions:
    """Unit tests for exception handling"""
    
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.list_certificates')
    @patch('invoice_cdk.lambdas.consumo_timbres_handler.valida_cors')
    def test_exception_handling(self, mock_valida_cors, mock_list_certificates):
        """Test that exceptions are properly caught and returned"""
        import invoice_cdk.lambdas.consumo_timbres_handler as consumo_timbres_handler
        
        # Setup mocks to raise exception
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_list_certificates.side_effect = Exception("Database connection error")
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"usuario": "test_user@example.com"},
            "queryStringParameters": {"desde": "2024-01-01", "hasta": "2024-01-31"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = consumo_timbres_handler.lambda_handler(event, {})
        
        # Assertions
        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert "Database connection error" in body["error"]
