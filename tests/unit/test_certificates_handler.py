"""
Unit tests for certificates_handler.
These tests use mocks and do not require a database connection.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from http import HTTPStatus
from bson import ObjectId
from datetime import datetime


@pytest.fixture
def sample_certificate_data():
    """Sample certificate data for testing"""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "nombre": "Test Certificate",
        "rfc": "TEST123456ABC",
        "no_certificado": "30001000000400002345",
        "desde": "2023-01-01T00:00:00",
        "hasta": "2027-12-31T23:59:59",
        "sucursales": [],
        "usuario": "test_user@example.com"
    }


@pytest.fixture
def sample_sucursal_data():
    """Sample sucursal data for testing"""
    return {
        "_id": "507f1f77bcf86cd799439012",
        "codigo_sucursal": "SUC001",
        "nombre": "Sucursal Test"
    }


class TestCertificatesHandlerPost:
    """Unit tests for POST method (create certificate)"""
    
    @patch('invoice_cdk.lambdas.certificates_handler.add_certificate')
    @patch('invoice_cdk.lambdas.certificates_handler.Certificado')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_create_certificate_success(self, mock_valida_cors, mock_certificado_class,
                                       mock_add_certificate, sample_certificate_data):
        """Test successful certificate creation"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_certificado_instance = MagicMock()
        mock_certificado_class.return_value = mock_certificado_instance
        mock_add_certificate.return_value = ObjectId("507f1f77bcf86cd799439011")
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_certificate_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.CREATED
        body = json.loads(response["body"])
        assert "id" in body
        assert body["message"] == "Certificate added"
        mock_certificado_class.assert_called_once()
        mock_add_certificate.assert_called_once()
    
    @patch('invoice_cdk.lambdas.certificates_handler.Certificado')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_create_certificate_invalid_data(self, mock_valida_cors, mock_certificado_class):
        """Test certificate creation with invalid data"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks to raise validation error
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_certificado_class.side_effect = KeyError("Missing required field")
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({"invalid": "data"}),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.INTERNAL_SERVER_ERROR
        body = json.loads(response["body"])
        assert "error" in body


class TestCertificatesHandlerGet:
    """Unit tests for GET method (list certificates)"""
    
    @patch('invoice_cdk.lambdas.certificates_handler.get_sucursal_by_id')
    @patch('invoice_cdk.lambdas.certificates_handler.list_certificates')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_get_certificates_by_usuario_success(self, mock_valida_cors, mock_list_certificates,
                                                  mock_get_sucursal, sample_certificate_data,
                                                  sample_sucursal_data):
        """Test successful certificate retrieval by usuario"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        cert_data = sample_certificate_data.copy()
        cert_data["_id"] = ObjectId("507f1f77bcf86cd799439011")
        cert_data["desde"] = datetime(2023, 1, 1)
        cert_data["hasta"] = datetime(2027, 12, 31)
        cert_data["sucursales"] = [{"_id": ObjectId("507f1f77bcf86cd799439012")}]
        mock_list_certificates.return_value = [cert_data]
        
        sucursal_data = sample_sucursal_data.copy()
        sucursal_data["_id"] = ObjectId("507f1f77bcf86cd799439012")
        mock_get_sucursal.return_value = sucursal_data
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "test_user@example.com"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        mock_list_certificates.assert_called_once_with("test_user@example.com", 
                                                       certificates_handler.certificates_collection)
        mock_get_sucursal.assert_called_once()
    
    @patch('invoice_cdk.lambdas.certificates_handler.list_certificates')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_get_certificates_empty_list(self, mock_valida_cors, mock_list_certificates):
        """Test certificate retrieval when no certificates exist"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_list_certificates.return_value = []
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "user_with_no_certs@example.com"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        # The body should be a JSON array (empty)
        body = json.loads(response["body"])
        assert isinstance(body, list)
        assert len(body) == 0


class TestCertificatesHandlerPut:
    """Unit tests for PUT method (update certificate)"""
    
    @patch('invoice_cdk.lambdas.certificates_handler.update_certificate')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_update_certificate_success(self, mock_valida_cors, mock_update_certificate,
                                       sample_certificate_data):
        """Test successful certificate update"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_update_result.modified_count = 1
        mock_update_certificate.return_value = mock_update_result
        
        updated_data = sample_certificate_data.copy()
        updated_data["nombre"] = "Updated Certificate Name"
        
        event = {
            "httpMethod": "PUT",
            "pathParameters": {"id": "507f1f77bcf86cd799439011"},
            "body": json.dumps(updated_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Certificate updated"
        mock_update_certificate.assert_called_once()


class TestCertificatesHandlerDelete:
    """Unit tests for DELETE method (delete certificate)"""
    
    @patch('invoice_cdk.lambdas.certificates_handler.delete_certificate')
    @patch('invoice_cdk.lambdas.certificates_handler.delete_sucursal')
    @patch('invoice_cdk.lambdas.certificates_handler.get_certificate_by_id')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_delete_certificate_with_sucursales(self, mock_valida_cors, mock_get_certificate,
                                                mock_delete_sucursal, mock_delete_certificate,
                                                sample_certificate_data):
        """Test certificate deletion with associated sucursales"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        cert_with_sucursales = sample_certificate_data.copy()
        cert_with_sucursales["sucursales"] = [
            {"_id": "507f1f77bcf86cd799439012", "codigo_sucursal": "SUC001"}
        ]
        mock_get_certificate.return_value = cert_with_sucursales
        
        # Mock folio_collection delete
        certificates_handler.folio_collection.delete_one = MagicMock()
        
        event = {
            "httpMethod": "DELETE",
            "pathParameters": {"id": "507f1f77bcf86cd799439011"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Certificate deleted"
        mock_get_certificate.assert_called_once()
        mock_delete_sucursal.assert_called_once()
        mock_delete_certificate.assert_called_once()
        certificates_handler.folio_collection.delete_one.assert_called_once()
    
    @patch('invoice_cdk.lambdas.certificates_handler.delete_certificate')
    @patch('invoice_cdk.lambdas.certificates_handler.get_certificate_by_id')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_delete_certificate_without_sucursales(self, mock_valida_cors, mock_get_certificate,
                                                   mock_delete_certificate, sample_certificate_data):
        """Test certificate deletion without sucursales"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        cert_without_sucursales = sample_certificate_data.copy()
        cert_without_sucursales["sucursales"] = []
        mock_get_certificate.return_value = cert_without_sucursales
        
        event = {
            "httpMethod": "DELETE",
            "pathParameters": {"id": "507f1f77bcf86cd799439011"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Certificate deleted"
        mock_delete_certificate.assert_called_once()


class TestCertificatesHandlerExceptions:
    """Unit tests for exception handling"""
    
    @patch('invoice_cdk.lambdas.certificates_handler.list_certificates')
    @patch('invoice_cdk.lambdas.certificates_handler.valida_cors')
    def test_exception_handling(self, mock_valida_cors, mock_list_certificates):
        """Test that exceptions are properly caught and returned"""
        import invoice_cdk.lambdas.certificates_handler as certificates_handler
        
        # Setup mocks to raise exception
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_list_certificates.side_effect = Exception("Database connection error")
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "test_user@example.com"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = certificates_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.INTERNAL_SERVER_ERROR
        body = json.loads(response["body"])
        assert "error" in body
        assert "Database connection error" in body["error"]
