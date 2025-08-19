#!/bin/bash

# Main test runner for all brack tool tests
# Executes unit tests, edge case tests, and cleanup validation tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test suite tracking
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

run_test_suite() {
    local suite_name="$1"
    local test_script="$2"
    
    TOTAL_SUITES=$((TOTAL_SUITES + 1))
    
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}Running Test Suite: $suite_name${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
    
    if "$test_script"; then
        echo -e "${GREEN}✓ Test Suite PASSED: $suite_name${NC}"
        PASSED_SUITES=$((PASSED_SUITES + 1))
    else
        echo -e "${RED}✗ Test Suite FAILED: $suite_name${NC}"
        FAILED_SUITES=$((FAILED_SUITES + 1))
    fi
    echo ""
}

main() {
    echo -e "${BLUE}Brack Tool Comprehensive Test Suite${NC}"
    echo -e "${BLUE}===================================${NC}"
    echo ""
    
    # Ensure we're in the right directory
    cd "$SCRIPT_DIR"
    
    # Validate test scripts exist and are executable
    local test_scripts=(
        "test_brack.sh"
        "test_edge_cases.sh"
    )
    
    for script in "${test_scripts[@]}"; do
        if [[ ! -f "$script" ]]; then
            echo -e "${RED}ERROR: Test script not found: $script${NC}"
            exit 1
        fi
        
        if [[ ! -x "$script" ]]; then
            echo -e "${RED}ERROR: Test script not executable: $script${NC}"
            echo "Run: chmod +x $script"
            exit 1
        fi
    done
    
    # Validate main brack script exists
    if [[ ! -f "brack" ]]; then
        echo -e "${RED}ERROR: Main brack script not found${NC}"
        exit 1
    fi
    
    # Run all test suites
    run_test_suite "Unit Tests" "./test_brack.sh"
    run_test_suite "Edge Case Tests" "./test_edge_cases.sh"
    
    # Print final results
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}FINAL TEST RESULTS${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
    echo "Test suites run: $TOTAL_SUITES"
    echo -e "Test suites passed: ${GREEN}$PASSED_SUITES${NC}"
    echo -e "Test suites failed: ${RED}$FAILED_SUITES${NC}"
    echo ""
    
    if [[ $FAILED_SUITES -eq 0 ]]; then
        echo -e "${GREEN}🎉 ALL TEST SUITES PASSED! 🎉${NC}"
        echo -e "${GREEN}The brack tool is ready for production use.${NC}"
        return 0
    else
        echo -e "${RED}❌ SOME TEST SUITES FAILED${NC}"
        echo -e "${RED}Please review the failures above before deploying.${NC}"
        return 1
    fi
}

# Run main function
main "$@"