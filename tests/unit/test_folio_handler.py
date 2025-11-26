"""
Unit tests for folio_handler.
These tests use mocks and do not require a database connection.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from http import HTTPStatus
from bson import ObjectId


@pytest.fixture
def sample_folio_data():
    """Sample folio data for testing"""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "sucursal": "SUC001",
        "noFolio": 1
    }


class TestFolioHandlerPost:
    """Unit tests for POST method (create folio)"""
    
    @patch('invoice_cdk.lambdas.folio_handler.folio_collection')
    @patch('invoice_cdk.lambdas.folio_handler.Folio')
    @patch('invoice_cdk.lambdas.folio_handler.valida_cors')
    def test_create_folio_success(self, mock_valida_cors, mock_folio_class,
                                  mock_folio_collection, sample_folio_data):
        """Test successful folio creation"""
        import invoice_cdk.lambdas.folio_handler as folio_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_folio_instance = MagicMock()
        mock_folio_instance.sucursal = "SUC001"
        mock_folio_instance.dict.return_value = sample_folio_data
        mock_folio_class.return_value = mock_folio_instance
        
        # Mock find_one to return None (folio doesn't exist)
        mock_folio_collection.find_one.return_value = None
        
        # Mock insert_one
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        mock_folio_collection.insert_one.return_value = mock_insert_result
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_folio_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.CREATED
        body = json.loads(response["body"])
        assert "id_folio" in body
        mock_folio_collection.find_one.assert_called_once_with({"sucursal": "SUC001"})
        mock_folio_collection.insert_one.assert_called_once()
    
    @patch('invoice_cdk.lambdas.folio_handler.folio_collection')
    @patch('invoice_cdk.lambdas.folio_handler.Folio')
    @patch('invoice_cdk.lambdas.folio_handler.valida_cors')
    def test_create_folio_already_exists(self, mock_valida_cors, mock_folio_class,
                                         mock_folio_collection, sample_folio_data):
        """Test folio creation when folio already exists"""
        import invoice_cdk.lambdas.folio_handler as folio_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_folio_instance = MagicMock()
        mock_folio_instance.sucursal = "SUC001"
        mock_folio_class.return_value = mock_folio_instance
        
        # Mock find_one to return existing folio
        mock_folio_collection.find_one.return_value = sample_folio_data
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_folio_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.ACCEPTED
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio already exists"
        mock_folio_collection.find_one.assert_called_once()
        mock_folio_collection.insert_one.assert_not_called()


class TestFolioHandlerGet:
    """Unit tests for GET method (retrieve folio)"""
    
    @patch('invoice_cdk.lambdas.folio_handler.folio_collection')
    @patch('invoice_cdk.lambdas.folio_handler.valida_cors')
    def test_get_folio_by_sucursal_success(self, mock_valida_cors, mock_folio_collection,
                                           sample_folio_data):
        """Test successful folio retrieval by sucursal"""
        import invoice_cdk.lambdas.folio_handler as folio_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        folio_data = sample_folio_data.copy()
        folio_data["_id"] = ObjectId("507f1f77bcf86cd799439011")
        mock_folio_collection.find_one.return_value = folio_data
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"sucursal": "SUC001"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert "folio" in body
        assert body["folio"]["sucursal"] == "SUC001"
        mock_folio_collection.find_one.assert_called_once_with({"sucursal": "SUC001"})
    
    @patch('invoice_cdk.lambdas.folio_handler.folio_collection')
    @patch('invoice_cdk.lambdas.folio_handler.valida_cors')
    def test_get_folio_not_found(self, mock_valida_cors, mock_folio_collection):
        """Test folio retrieval when folio doesn't exist"""
        import invoice_cdk.lambdas.folio_handler as folio_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_folio_collection.find_one.return_value = None
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"sucursal": "NONEXISTENT"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.NOT_FOUND
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio not found"


class TestFolioHandlerPut:
    """Unit tests for PUT method (update folio)"""
    
    @patch('invoice_cdk.lambdas.folio_handler.folio_collection')
    @patch('invoice_cdk.lambdas.folio_handler.valida_cors')
    def test_update_folio_success(self, mock_valida_cors, mock_folio_collection,
                                  sample_folio_data):
        """Test successful folio update"""
        import invoice_cdk.lambdas.folio_handler as folio_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        
        # Mock UpdateResult
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_update_result.modified_count = 1
        mock_folio_collection.update_one.return_value = mock_update_result
        
        update_data = {
            "codigo_sucursal": "SUC001",
            "folio": 100
        }
        
        event = {
            "httpMethod": "PUT",
            "body": json.dumps(update_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio updated"
        mock_folio_collection.update_one.assert_called_once_with(
            {"sucursal": "SUC001"}, 
            {"$set": {"noFolio": 100}}
        )
    
    @patch('invoice_cdk.lambdas.folio_handler.folio_collection')
    @patch('invoice_cdk.lambdas.folio_handler.valida_cors')
    def test_update_folio_not_found(self, mock_valida_cors, mock_folio_collection):
        """Test folio update when folio doesn't exist"""
        import invoice_cdk.lambdas.folio_handler as folio_handler
        
        # Setup mocks
        mock_valida_cors.return_value = "http://localhost:3000"
        
        # Mock UpdateResult with no matches
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 0
        mock_folio_collection.update_one.return_value = mock_update_result
        
        update_data = {
            "codigo_sucursal": "NONEXISTENT",
            "folio": 100
        }
        
        event = {
            "httpMethod": "PUT",
            "body": json.dumps(update_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.NOT_FOUND
        body = json.loads(response["body"])
        assert body["mensaje"] == "Folio not found"


class TestFolioHandlerExceptions:
    """Unit tests for exception handling"""
    
    @patch('invoice_cdk.lambdas.folio_handler.folio_collection')
    @patch('invoice_cdk.lambdas.folio_handler.valida_cors')
    def test_exception_handling(self, mock_valida_cors, mock_folio_collection):
        """Test that exceptions are properly caught and returned"""
        import invoice_cdk.lambdas.folio_handler as folio_handler
        
        # Setup mocks to raise exception
        mock_valida_cors.return_value = "http://localhost:3000"
        mock_folio_collection.find_one.side_effect = Exception("Database connection error")
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"sucursal": "SUC001"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = folio_handler.handler(event, {})
        
        # Assertions
        assert response["statusCode"] == HTTPStatus.INTERNAL_SERVER_ERROR
        body = json.loads(response["body"])
        assert "error" in body
        assert "Database connection error" in body["error"]
