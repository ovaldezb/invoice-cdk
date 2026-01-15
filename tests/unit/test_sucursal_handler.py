import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from http import HTTPStatus
from bson import ObjectId

# Don't import here - let it be imported after mocks are setup


@pytest.fixture(scope='module')
def sucursal_handler_module():
    """Import sucursal_handler after mocks are setup"""
    import invoice_cdk.lambdas.sucursal_handler as sucursal_handler
    return sucursal_handler



@pytest.fixture
def sample_sucursal_data():
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
        "id_certificado": "68fa9bb5b5ae2b81154d5af9"
    }


@pytest.fixture
def sample_sucursal_response():
    """Sample sucursal response from DB"""
    return {
        "_id": "68fab3e28f518fe7ff713f2e",
        "codigo_sucursal": "378",
        "serie": "OPI",
        "direccion": "Vialidad de la Barranca 6 PB 27",
        "codigo_postal": "52787",
        "responsable": "Cesar Esquivel",
        "telefono": "5544889270",
        "regimen_fiscal": "601",
        "folio": "1",
        "id_certificado": "68fa9bb5b5ae2b81154d5af9"
    }


class TestSucursalHandlerPost:
    """Test POST method - Create sucursal"""
    
    @patch('invoice_cdk.lambdas.sucursal_handler.add_sucursal')
    @patch('invoice_cdk.lambdas.sucursal_handler.valida_cors')
    @patch('invoice_cdk.lambdas.sucursal_handler.Sucursal')
    def test_create_sucursal_success(self, mock_sucursal_class, mock_cors, mock_add, 
                                     sucursal_handler_module, sample_sucursal_data):
        """Test successful sucursal creation"""
        mock_cors.return_value = "*"
        mock_add.return_value = ObjectId("68fab3e28f518fe7ff713f2e")
        mock_sucursal_instance = Mock()
        mock_sucursal_class.return_value = mock_sucursal_instance
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps(sample_sucursal_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler_module.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.CREATED
        body = json.loads(response["body"])
        assert "id" in body
        assert body["message"] == "Sucursal added"
        mock_add.assert_called_once()
    
    @patch('invoice_cdk.lambdas.sucursal_handler.valida_cors')
    @patch('invoice_cdk.lambdas.sucursal_handler.Sucursal')
    def test_create_sucursal_invalid_data(self, mock_sucursal_class, mock_cors, sucursal_handler_module):
        """Test creation with invalid data"""
        mock_cors.return_value = "*"
        mock_sucursal_class.side_effect = Exception("Invalid data")
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({"invalid": "data"}),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler_module.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.INTERNAL_SERVER_ERROR
        body = json.loads(response["body"])
        assert "error" in body


class TestSucursalHandlerGet:
    """Test GET method - Retrieve sucursales"""
    
    @patch('invoice_cdk.lambdas.sucursal_handler.get_sucursal_by_codigo')
    @patch('invoice_cdk.lambdas.sucursal_handler.valida_cors')
    def test_get_sucursal_by_id_success(self, mock_cors, mock_get, sucursal_handler_module,
                                       sample_sucursal_response):
        """Test successful retrieval of specific sucursal"""
        mock_cors.return_value = "*"
        mock_get.return_value = sample_sucursal_response
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "378"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler_module.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["codigo_sucursal"] == "378"
        assert body["serie"] == "OPI"
    
    @patch('invoice_cdk.lambdas.sucursal_handler.get_sucursal_by_codigo')
    @patch('invoice_cdk.lambdas.sucursal_handler.valida_cors')
    def test_get_sucursal_by_id_not_found(self, mock_cors, mock_get, sucursal_handler_module):
        """Test retrieval of non-existent sucursal"""
        mock_cors.return_value = "*"
        mock_get.return_value = None
        
        event = {
            "httpMethod": "GET",
            "pathParameters": {"id": "999"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler_module.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.NOT_FOUND
        body = json.loads(response["body"])
        assert body["error"] == "Sucursal not found"
    
    @patch('invoice_cdk.lambdas.sucursal_handler.valida_cors')
    def test_get_all_sucursales(self, mock_cors, sucursal_handler_module):
        """Test retrieval of all sucursales"""
        mock_cors.return_value = "*"
        
        # Mock the collection find method to return a list
        mock_find_result = [
            {
                "_id": ObjectId("68fab3e28f518fe7ff713f2e"),
                "codigo_sucursal": "378",
                "serie": "OPI"
            },
            {
                "_id": ObjectId("68fab3e28f518fe7ff713f2f"),
                "codigo_sucursal": "379",
                "serie": "OPI"
            }
        ]
        
        # Patch list() to return the mock data
        with patch('invoice_cdk.lambdas.sucursal_handler.list', return_value=mock_find_result):
            event = {
                "httpMethod": "GET",
                "headers": {"origin": "http://localhost:3000"}
            }
        
            response = sucursal_handler_module.handler(event, {})
        
            assert response["statusCode"] == HTTPStatus.OK
            body = json.loads(response["body"])
            assert len(body) == 2


class TestSucursalHandlerPut:
    """Test PUT method - Update sucursal"""
    
    @patch('invoice_cdk.lambdas.sucursal_handler.get_sucursal_by_id')
    @patch('invoice_cdk.lambdas.sucursal_handler.update_sucursal')
    @patch('invoice_cdk.lambdas.sucursal_handler.valida_cors')
    def test_update_sucursal_success(self, mock_cors, mock_update, mock_get, sucursal_handler_module,
                                     sample_sucursal_response):
        """Test successful sucursal update"""
        mock_cors.return_value = "*"
        updated_data = sample_sucursal_response.copy()
        updated_data["responsable"] = "Juan Perez"
        mock_get.return_value = updated_data
        
        event = {
            "httpMethod": "PUT",
            "pathParameters": {"id": "68fab3e28f518fe7ff713f2e"},
            "body": json.dumps(updated_data),
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler_module.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Sucursal updated"


class TestSucursalHandlerDelete:
    """Test DELETE method - Delete sucursal"""
    
    @patch('invoice_cdk.lambdas.sucursal_handler.delete_sucursal')
    @patch('invoice_cdk.lambdas.sucursal_handler.update_certificate')
    @patch('invoice_cdk.lambdas.sucursal_handler.get_certificate_by_id')
    @patch('invoice_cdk.lambdas.sucursal_handler.get_sucursal_by_id')
    @patch('invoice_cdk.lambdas.sucursal_handler.valida_cors')
    def test_delete_sucursal_success(self, mock_cors, mock_get_suc, mock_get_cert, 
                                     mock_update_cert, mock_delete, sucursal_handler_module):
        """Test successful sucursal deletion"""
        mock_cors.return_value = "*"
        mock_get_suc.return_value = {
            "_id": "68fab3e28f518fe7ff713f2e",
            "codigo_sucursal": "378",
            "id_certificado": "68fa9bb5b5ae2b81154d5af9"
        }
        mock_get_cert.return_value = {
            "_id": "68fa9bb5b5ae2b81154d5af9",
            "sucursales": [
                {"_id": "68fab3e28f518fe7ff713f2e", "codigo": "378"}
            ]
        }
        
        # Mock folio_collection
        sucursal_handler_module.folio_collection.delete_one = Mock()
        
        event = {
            "httpMethod": "DELETE",
            "pathParameters": {"id": "68fab3e28f518fe7ff713f2e"},
            "headers": {"origin": "http://localhost:3000"}
        }
        
        response = sucursal_handler_module.handler(event, {})
        
        assert response["statusCode"] == HTTPStatus.OK
        body = json.loads(response["body"])
        assert body["message"] == "Sucursal deleted"
