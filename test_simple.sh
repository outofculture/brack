#!/bin/bash

# Simple validation test for brack tool
# Tests core functionality without complex mocking

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRACK_SCRIPT="$SCRIPT_DIR/brack"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

test_count=0
pass_count=0
fail_count=0

run_simple_test() {
    local test_name="$1"
    local test_command="$2"
    
    test_count=$((test_count + 1))
    echo -e "${BLUE}Testing: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASS${NC}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}✗ FAIL${NC}"
        fail_count=$((fail_count + 1))
    fi
    echo
}

main() {
    echo -e "${BLUE}Brack Tool Simple Validation Tests${NC}"
    echo "========================================"
    echo
    
    cd "$SCRIPT_DIR"
    
    # Test 1: Script exists and is executable
    run_simple_test "Script executable" "[[ -x '$BRACK_SCRIPT' ]]"
    
    # Test 2: Help output works
    run_simple_test "Help output" "$BRACK_SCRIPT --help >/dev/null 2>&1"
    
    # Test 3: Version output works  
    run_simple_test "Version output" "$BRACK_SCRIPT --version >/dev/null 2>&1"
    
    # Test 4: Fails appropriately with no arguments
    run_simple_test "No args handling" "! $BRACK_SCRIPT >/dev/null 2>&1"
    
    # Test 5: Script validates git repository requirement
    temp_dir=$(mktemp -d)
    cd "$temp_dir"
    run_simple_test "Non-git directory detection" "! $BRACK_SCRIPT test.py >/dev/null 2>&1"
    cd "$SCRIPT_DIR"
    rm -rf "$temp_dir"
    
    # Test 6: Script validates file extensions
    temp_git_dir=$(mktemp -d)
    cd "$temp_git_dir"
    git init --quiet
    git config user.name "Test"
    git config user.email "test@test.com"
    echo "test" > README.md
    git add README.md
    git commit -m "Initial" --quiet
    git checkout -b main --quiet 2>/dev/null || git branch -M main --quiet
    
    echo "test content" > test.txt
    run_simple_test "Non-Python file rejection" "! $BRACK_SCRIPT test.txt >/dev/null 2>&1"
    
    cd "$SCRIPT_DIR"
    rm -rf "$temp_git_dir"
    
    # Test 7: Error state file creation/cleanup
    error_file="AUTO-BLACK-FORMATTING-ERROR"
    rm -f "$error_file"
    echo "test error" > "$error_file"
    run_simple_test "Error state blocking" "! $BRACK_SCRIPT --help >/dev/null 2>&1"
    run_simple_test "Error state cleanup" "$BRACK_SCRIPT --cleanup >/dev/null 2>&1"
    run_simple_test "Error state removed" "[[ ! -f '$error_file' ]]"
    
    # Results
    echo "========================================"
    echo -e "${BLUE}Simple Test Results${NC}"
    echo "Tests run: $test_count"
    echo -e "Passed: ${GREEN}$pass_count${NC}"
    echo -e "Failed: ${RED}$fail_count${NC}"
    
    if [[ $fail_count -eq 0 ]]; then
        echo -e "${GREEN}✓ All simple validation tests passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        return 1
    fi
}

main "$@"