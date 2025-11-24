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
echo -e "${YELLOW}  Running Tests${NC}"
echo -e "${YELLOW}=====================================${NC}\n"

# Load environment variables from .env_dev file for testing
if [ -f .env_dev ]; then
    echo -e "${GREEN}Loading environment variables from .env_dev file...${NC}"
    export $(grep -v '^#' .env_dev | xargs)
    echo -e "${GREEN}Environment variables loaded successfully${NC}\n"
else
    echo -e "${RED}Error: .env_dev file not found!${NC}"
    echo -e "${YELLOW}Please create a .env_dev file with your test environment variables${NC}\n"
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="/Users/macbookpro/git/invoice-cdk/requirements:$(pwd):$(pwd)/invoice_cdk:$PYTHONPATH"

# Check if pytest exists in requirements directory
PYTEST_CMD="python -m pytest"
if [ -f "./requirements/bin/pytest" ]; then
    PYTEST_CMD="./requirements/bin/pytest"
elif [ -f "./requirements/pytest" ]; then
    PYTEST_CMD="python ./requirements/pytest"
fi

echo -e "${GREEN}Using pytest from requirements directory${NC}\n"

# Function to run tests
run_tests() {
    local test_path=$1
    local test_name=$2
    
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Running ${test_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    $PYTEST_CMD $test_path \
        -v \
        --cov=invoice_cdk/lambdas/sucursal_handler \
        --cov-append \
        --cov-report=term-missing \
        --tb=short
    
    return $?
}

# Initialize coverage
rm -f .coverage 2>/dev/null

# Run tests based on argument
case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}Running only Unit Tests (with mocks)${NC}\n"
        run_tests "tests/unit/test_sucursal_handler.py" "Unit Tests"
        TEST_RESULT=$?
        ;;
    integration)
        echo -e "${YELLOW}Running only Integration Tests (with real DB)${NC}\n"
        run_tests "tests/integration/test_sucursal_handler_integration.py" "Integration Tests"
        TEST_RESULT=$?
        ;;
    all)
        echo -e "${YELLOW}Running All Tests (Unit + Integration)${NC}\n"
        
        # Run unit tests first
        run_tests "tests/unit/test_sucursal_handler.py" "Unit Tests"
        UNIT_RESULT=$?
        
        # Run integration tests
        run_tests "tests/integration/test_sucursal_handler_integration.py" "Integration Tests"
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

# Generate final coverage reports
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Generating Coverage Reports${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    $PYTEST_CMD --cov=invoice_cdk/lambdas/sucursal_handler \
        --cov-report=html \
        --cov-report=xml \
        --cache-clear \
        tests/ > /dev/null 2>&1
    
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "\n${GREEN}Coverage report generated:${NC}"
    echo -e "  HTML: ${YELLOW}htmlcov/index.html${NC}"
    echo -e "  XML:  ${YELLOW}coverage.xml${NC}"
    
    # Open HTML coverage report (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "\n${GREEN}Opening coverage report in browser...${NC}"
        open htmlcov/index.html
    fi
else
    echo -e "\n${RED}✗ Tests failed!${NC}"
    
    if [ "$TEST_TYPE" = "all" ]; then
        echo -e "\n${YELLOW}Test Results Summary:${NC}"
        [ $UNIT_RESULT -eq 0 ] && echo -e "  Unit Tests:        ${GREEN}✓ PASSED${NC}" || echo -e "  Unit Tests:        ${RED}✗ FAILED${NC}"
        [ $INTEGRATION_RESULT -eq 0 ] && echo -e "  Integration Tests: ${GREEN}✓ PASSED${NC}" || echo -e "  Integration Tests: ${RED}✗ FAILED${NC}"
    fi
    
    exit 1
fi

echo -e "\n${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Test Execution Complete${NC}"
echo -e "${YELLOW}=====================================${NC}\n"
