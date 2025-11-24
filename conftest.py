import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add project paths to sys.path FIRST
project_root = Path(__file__).parent
lambdas_path = project_root / 'invoice_cdk' / 'lambdas'
requirements_path = project_root / 'requirements'

for path in [project_root, lambdas_path, requirements_path]:
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


# Load .env_dev file before running tests
def pytest_configure(config):
    """Load environment variables from .env_dev file for testing"""
    env_file = Path(__file__).parent / '.env_dev'
    if env_file.exists():
        print(f"\n🔧 Loading test environment variables from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
        print("✅ Test environment variables loaded successfully\n")
    else:
        print(f"\n⚠️  Warning: .env_dev file not found at {env_file}")
        print("Please create a .env_dev file with your test environment variables\n")


@pytest.fixture(scope='session', autouse=True)
def setup_mocks():
    """Setup all module mocks at session start, AFTER coverage starts"""
    # Setup constants mock
    mock_constants_class = type('Constants', (), {
        'HEADERS': {},
        'POST': "POST",
        'GET': "GET",
        'PUT': "PUT",
        'DELETE': "DELETE",
        'STATUS_CODE': "statusCode",
        'BODY': "body",
        'HEADERS_KEY': "headers"
    })
    
    mock_constants_module = type(sys)('constantes')
    mock_constants_module.Constants = mock_constants_class
    
    # Mock modules that sucursal_handler depends on
    sys.modules['constantes'] = mock_constants_module
    sys.modules['receptor_handler'] = MagicMock()
    sys.modules['dbaccess.db_sucursal'] = MagicMock()
    sys.modules['dbaccess.db_certificado'] = MagicMock()
    sys.modules['models.sucursal'] = MagicMock()
    
    # Setup MongoDB mocks
    mock_collection = MagicMock()
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    mock_client_instance = MagicMock()
    mock_client_instance.__getitem__ = MagicMock(return_value=mock_db)
    
    # Patch MongoClient
    patcher = patch('pymongo.MongoClient', return_value=mock_client_instance)
    mock_client = patcher.start()
    
    yield
    
    patcher.stop()
