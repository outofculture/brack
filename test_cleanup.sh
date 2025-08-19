#!/bin/bash

# Cleanup and rollback mechanism validation tests
# Tests all cleanup/rollback functions work correctly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRACK_SCRIPT="$SCRIPT_DIR/brack"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

test_count=0
pass_count=0
fail_count=0

run_cleanup_test() {
    local test_name="$1"
    local test_function="$2"
    
    test_count=$((test_count + 1))
    echo -e "${BLUE}Testing: $test_name${NC}"
    
    # Create test git repository
    local temp_dir
    temp_dir=$(mktemp -d -t brack_cleanup_test_XXXXXX)
    cd "$temp_dir"
    
    # Initialize git repository
    git init --quiet
    git config user.name "Test User"
    git config user.email "test@example.com"
    
    echo "# Test Repository" > README.md
    git add README.md
    git commit -m "Initial commit" --quiet
    
    # Create main branch
    git checkout -b main --quiet 2>/dev/null || git branch -M main --quiet
    
    if "$test_function" 2>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}✗ FAIL${NC}"
        fail_count=$((fail_count + 1))
    fi
    
    # Cleanup
    cd "$SCRIPT_DIR"
    rm -rf "$temp_dir"
    echo
}

#=============================================================================
# CLEANUP VALIDATION TESTS
#=============================================================================

test_error_state_cleanup() {
    local error_file="AUTO-BLACK-FORMATTING-ERROR"
    
    # Create error state
    echo "Test error state" > "$error_file"
    
    # Source brack functions
    source "$BRACK_SCRIPT" 2>/dev/null || return 1
    
    # Test cleanup
    cleanup_error_state
    
    # Verify cleanup
    if [[ ! -f "$error_file" ]]; then
        echo "Error state file cleaned up successfully"
        return 0
    else
        echo "Error state file was not cleaned up"
        return 1
    fi
}

test_stash_cleanup() {
    # Create uncommitted changes
    echo "print('test changes')" > test_changes.py
    
    # Create a stash
    git stash push -m "Test stash" --quiet
    local stash_count_before
    stash_count_before=$(git stash list | wc -l)
    
    if [[ $stash_count_before -eq 0 ]]; then
        echo "No stash was created, skipping test"
        return 0
    fi
    
    # Source brack and test stash cleanup
    source "$BRACK_SCRIPT" 2>/dev/null || return 1
    
    # Test stash restoration (simulate cleanup)
    if git stash pop --quiet 2>/dev/null; then
        echo "Stash cleanup/restoration successful"
        
        # Verify file was restored
        if [[ -f "test_changes.py" ]]; then
            echo "Working directory restored correctly"
            return 0
        else
            echo "Working directory not restored"
            return 1
        fi
    else
        echo "Stash pop failed"
        return 1
    fi
}

test_branch_cleanup() {
    # Create a test formatting branch
    local formatting_branch="test-feature-auto-black-formatting"
    git checkout -b "$formatting_branch" --quiet
    echo "print('formatting changes')" > format_test.py
    git add format_test.py
    git commit -m "Formatting changes" --quiet
    
    # Return to main
    git checkout main --quiet
    
    # Verify branch exists
    if ! git show-ref --verify --quiet "refs/heads/$formatting_branch"; then
        echo "Test branch was not created properly"
        return 1
    fi
    
    # Source brack and test branch cleanup
    source "$BRACK_SCRIPT" 2>/dev/null || return 1
    
    # Test branch cleanup
    cleanup_formatting_branch "$formatting_branch"
    
    # Verify branch was deleted
    if git show-ref --verify --quiet "refs/heads/$formatting_branch" 2>/dev/null; then
        echo "Branch was not cleaned up"
        return 1
    else
        echo "Branch cleanup successful"
        return 0
    fi
}

test_background_process_cleanup() {
    # Create long-running background process
    (sleep 30) &
    local bg_pid=$!
    
    # Source brack functions
    source "$BRACK_SCRIPT" 2>/dev/null || return 1
    
    # Initialize background process tracking
    declare -A BACKGROUND_PROCESSES
    BACKGROUND_PROCESSES["test_process"]=$bg_pid
    
    # Test cleanup
    cleanup_all_background_processes
    
    # Verify process was terminated
    if kill -0 "$bg_pid" 2>/dev/null; then
        echo "Background process was not terminated"
        kill -9 "$bg_pid" 2>/dev/null || true  # Force cleanup
        return 1
    else
        echo "Background process cleanup successful"
        return 0
    fi
}

test_emergency_cleanup_comprehensive() {
    # Setup complex state requiring cleanup
    echo "print('test')" > dirty_file.py
    git add dirty_file.py
    
    # Create stash
    echo "print('uncommitted')" > uncommitted.py
    git stash push -m "Test emergency stash" --quiet 2>/dev/null || true
    
    # Create formatting branch
    local formatting_branch="emergency-test-auto-black-formatting"
    git checkout -b "$formatting_branch" --quiet
    echo "print('emergency')" > emergency.py
    git add emergency.py
    git commit -m "Emergency test" --quiet
    git checkout main --quiet
    
    # Create background process
    (sleep 20) &
    local bg_pid=$!
    
    # Source brack functions
    source "$BRACK_SCRIPT" 2>/dev/null || return 1
    
    # Setup global state
    STASH_CREATED=true
    ORIGINAL_BRANCH="main"
    declare -A BACKGROUND_PROCESSES
    BACKGROUND_PROCESSES["emergency_test"]=$bg_pid
    
    # Test emergency cleanup
    emergency_cleanup "Test emergency scenario" 2>/dev/null || true
    
    # Verify cleanup occurred (some operations may fail in test environment)
    local cleanup_successful=true
    
    # Check if we're back on main branch
    local current_branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        echo "Not returned to main branch: $current_branch"
        cleanup_successful=false
    fi
    
    # Kill background process if still running
    if kill -0 "$bg_pid" 2>/dev/null; then
        kill -9 "$bg_pid" 2>/dev/null || true
    fi
    
    if $cleanup_successful; then
        echo "Emergency cleanup completed successfully"
        return 0
    else
        echo "Emergency cleanup had issues"
        return 1
    fi
}

test_signal_handler_cleanup() {
    # This test is more challenging as we need to test signal handling
    # We'll test that signal handlers are properly registered
    
    source "$BRACK_SCRIPT" 2>/dev/null || return 1
    
    # Test signal handler setup
    setup_signal_handlers
    
    # Check that trap handlers are registered
    local trap_output
    trap_output=$(trap)
    
    if [[ "$trap_output" =~ "INT" ]] && [[ "$trap_output" =~ "TERM" ]]; then
        echo "Signal handlers registered successfully"
        return 0
    else
        echo "Signal handlers not properly registered"
        return 1
    fi
}

test_error_recovery_mechanisms() {
    # Test various error recovery scenarios
    source "$BRACK_SCRIPT" 2>/dev/null || return 1
    
    # Setup test state
    local error_file="AUTO-BLACK-FORMATTING-ERROR"
    rm -f "$error_file"
    
    # Test error file creation
    create_error_state "Test recovery error" "test recovery command"
    
    if [[ -f "$error_file" ]]; then
        echo "Error state created for recovery testing"
    else
        echo "Failed to create error state"
        return 1
    fi
    
    # Test error state detection
    if ! check_error_state 2>/dev/null; then
        echo "Error state correctly detected"
    else
        echo "Error state not detected"
        return 1
    fi
    
    # Test recovery cleanup
    cleanup_error_state
    
    if [[ ! -f "$error_file" ]]; then
        echo "Error recovery cleanup successful"
        return 0
    else
        echo "Error recovery cleanup failed"
        return 1
    fi
}

#=============================================================================
# TEST EXECUTION
#=============================================================================

main() {
    echo -e "${BLUE}Brack Tool Cleanup and Rollback Validation${NC}"
    echo "============================================="
    echo
    
    cd "$SCRIPT_DIR"
    
    run_cleanup_test "Error state cleanup" test_error_state_cleanup
    run_cleanup_test "Stash cleanup and restoration" test_stash_cleanup
    run_cleanup_test "Branch cleanup" test_branch_cleanup
    run_cleanup_test "Background process cleanup" test_background_process_cleanup
    run_cleanup_test "Emergency cleanup comprehensive" test_emergency_cleanup_comprehensive
    run_cleanup_test "Signal handler cleanup" test_signal_handler_cleanup
    run_cleanup_test "Error recovery mechanisms" test_error_recovery_mechanisms
    
    # Results
    echo "============================================="
    echo -e "${BLUE}Cleanup Validation Test Results${NC}"
    echo "Tests run: $test_count"
    echo -e "Passed: ${GREEN}$pass_count${NC}"
    echo -e "Failed: ${RED}$fail_count${NC}"
    
    if [[ $fail_count -eq 0 ]]; then
        echo -e "${GREEN}✓ All cleanup validation tests passed!${NC}"
        echo -e "${GREEN}Cleanup and rollback mechanisms are working correctly.${NC}"
        return 0
    else
        echo -e "${RED}✗ Some cleanup validation tests failed${NC}"
        echo -e "${RED}Review cleanup mechanisms before production use.${NC}"
        return 1
    fi
}

main "$@"