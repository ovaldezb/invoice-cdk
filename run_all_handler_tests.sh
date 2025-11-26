#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
TEST_TYPE=${1:-all}  # Default to 'all' if no argument provided

echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Running Handler Tests${NC}"
echo -e "${YELLOW}  (ConsumoTimbres + Folio + Certificates + Receptor + DatosFactura + Sucursal + GeneraFactura)${NC}"
echo -e "${YELLOW}=====================================${NC}\n"

# Load environment variables from .env_test file for testing
if [ -f .env_test ]; then
    echo -e "${GREEN}Loading environment variables from .env_test file...${NC}"
    export $(grep -v '^#' .env_test | xargs)
    echo -e "${GREEN}Environment variables loaded successfully${NC}\n"
else
    echo -e "${RED}Error: .env_test file not found!${NC}"
    echo -e "${YELLOW}Please create a .env_test file with your test environment variables${NC}\n"
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="/Users/macbookpro/git/invoice-cdk/requirements:$(pwd):$(pwd)/invoice_cdk:$PYTHONPATH"

# Use Python from venv for proper coverage
PYTEST_CMD=".venv/bin/python -m pytest"

echo -e "${GREEN}Using pytest from venv${NC}\n"

# Initialize coverage
rm -f .coverage 2>/dev/null

# Define test files (receptor FIRST to avoid "previously imported" warning)
UNIT_TESTS="tests/unit/test_receptor_handler.py tests/unit/test_datos_factura_handler.py tests/unit/test_sucursal_handler.py tests/unit/test_certificates_handler.py tests/unit/test_folio_handler.py tests/unit/test_consumo_timbres_handler.py tests/unit/test_genera_factura_handler.py"
INTEGRATION_TESTS="tests/integration/test_receptor_handler_integration.py tests/integration/test_datos_factura_handler_integration.py tests/integration/test_sucursal_handler_integration.py tests/integration/test_certificates_handler_integration.py tests/integration/test_folio_handler_integration.py tests/integration/test_consumo_timbres_handler_integration.py tests/integration/test_genera_factura_handler_integration.py"

# Run tests based on argument
case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}Running only Unit Tests (with mocks)${NC}\n"
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  Running Unit Tests${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        
        $PYTEST_CMD $UNIT_TESTS \
            -v \
            --cov=invoice_cdk.lambdas.receptor_handler \
            --cov=invoice_cdk.lambdas.datos_factura_handler \
            --cov=invoice_cdk.lambdas.sucursal_handler \
            --cov=invoice_cdk.lambdas.certificates_handler \
            --cov=invoice_cdk.lambdas.folio_handler \
            --cov=invoice_cdk.lambdas.consumo_timbres_handler \
            --cov=invoice_cdk.lambdas.genera_factura_handler \
            --cov-report=term-missing \
            --cov-report=html \
            --cov-report=xml \
            --tb=short
        
        TEST_RESULT=$?
        ;;
    integration)
        echo -e "${YELLOW}Running only Integration Tests (with real DB)${NC}\n"
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  Running Integration Tests${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        
        $PYTEST_CMD $INTEGRATION_TESTS \
            -v \
            --cov=invoice_cdk.lambdas.receptor_handler \
            --cov=invoice_cdk.lambdas.datos_factura_handler \
            --cov=invoice_cdk.lambdas.sucursal_handler \
            --cov=invoice_cdk.lambdas.certificates_handler \
            --cov=invoice_cdk.lambdas.folio_handler \
            --cov=invoice_cdk.lambdas.consumo_timbres_handler \
            --cov=invoice_cdk.lambdas.genera_factura_handler \
            --cov-report=term-missing \
            --cov-report=html \
            --cov-report=xml \
            --tb=short
        
        TEST_RESULT=$?
        ;;
    all)
        echo -e "${YELLOW}Running All Tests (Unit + Integration)${NC}\n"
        
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  Running Unit Tests (no coverage)${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        
        # Run unit tests without coverage (they use mocks, so coverage is not meaningful)
        $PYTEST_CMD $UNIT_TESTS -v --tb=short
        UNIT_RESULT=$?
        
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BLUE}  Running Integration Tests (with coverage)${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
        
        # Run integration tests WITH coverage (they import real modules)
        $PYTEST_CMD $INTEGRATION_TESTS \
            -v \
            --cov=invoice_cdk.lambdas.receptor_handler \
            --cov=invoice_cdk.lambdas.datos_factura_handler \
            --cov=invoice_cdk.lambdas.sucursal_handler \
            --cov=invoice_cdk.lambdas.certificates_handler \
            --cov=invoice_cdk.lambdas.folio_handler \
            --cov=invoice_cdk.lambdas.consumo_timbres_handler \
            --cov=invoice_cdk.lambdas.genera_factura_handler \
            --cov-report=term-missing \
            --cov-report=html \
            --cov-report=xml \
            --tb=short
        
        INTEGRATION_RESULT=$?
        
        # Combined result
        if [ $UNIT_RESULT -eq 0 ] && [ $INTEGRATION_RESULT -eq 0 ]; then
            TEST_RESULT=0
        else
            TEST_RESULT=1
        fi
        ;;
    *)
        echo -e "${RED}Invalid argument: $TEST_TYPE${NC}"
        echo -e "${YELLOW}Usage: $0 [unit|integration|all]${NC}"
        echo -e "  unit        - Run only unit tests (with mocks)"
        echo -e "  integration - Run only integration tests (with real DB)"
        echo -e "  all         - Run both unit and integration tests (default)"
        exit 1
        ;;
esac

# Final results
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    echo -e "\n${GREEN}Coverage report generated:${NC}"
    echo -e "  HTML: ${YELLOW}htmlcov/index.html${NC}"
    echo -e "  XML:  ${YELLOW}coverage.xml${NC}"
    
    # Open HTML coverage report (macOS) in background
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "\n${GREEN}Opening coverage report in browser...${NC}"
        open htmlcov/index.html &
        # Give it a moment to open
        sleep 0.5
    fi
else
    echo -e "\n${RED}✗ Tests failed!${NC}"
    exit 1
fi

echo -e "\n${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Test Execution Complete${NC}"
echo -e "${YELLOW}=====================================${NC}\n"
