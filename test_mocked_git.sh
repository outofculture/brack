#!/bin/bash

# Mock git operations test for brack tool
# Tests git operations with consistent mocked responses

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRACK_SCRIPT="$SCRIPT_DIR/brack"

# Colors for output  
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Mock git function that provides predictable responses
mock_git() {
    case "$1" in
        "rev-parse")
            case "$2" in
                "--git-dir")
                    echo ".git"
                    return 0
                    ;;
                "--show-toplevel")
                    echo "/tmp/mock_git_repo"
                    return 0
                    ;;
                "HEAD")
                    echo "abc123def456"
                    return 0
                    ;;
            esac
            ;;
        "branch")
            case "$2" in
                "--show-current")
                    echo "feature/test-branch"
                    return 0
                    ;;
            esac
            ;;
        "status")
            case "$2" in
                "--porcelain")
                    # Return empty for clean working directory
                    return 0
                    ;;
            esac
            ;;
        "merge-base")
            echo "def456abc123"
            return 0
            ;;
        "show")
            # Mock file existence check
            if [[ "$2" =~ existing\.py$ ]]; then
                echo "print('existing file')"
                return 0
            else
                return 1  # File doesn't exist at commit
            fi
            ;;
        "checkout")
            return 0  # Always successful
            ;;
        "stash")
            case "$2" in
                "push")
                    echo "Saved working directory"
                    return 0
                    ;;
                "pop")
                    echo "Applied stash"
                    return 0
                    ;;
                "list")
                    echo "stash@{0}: WIP on feature: abc123 Test stash"
                    return 0
                    ;;
            esac
            ;;
        "add")
            return 0  # Always successful
            ;;
        "commit")
            echo "[test-branch abc123] black"
            return 0
            ;;
        "merge")
            return 0  # Always successful merge
            ;;
        "push")
            return 0  # Always successful push
            ;;
        "show-ref")
            case "$3" in
                "*formatting*")
                    return 0  # Branch exists
                    ;;
                *)
                    return 1  # Branch doesn't exist
                    ;;
            esac
            ;;
        *)
            # Default fallback to real git for unknown commands
            command git "$@"
            ;;
    esac
}

# Mock black command
mock_black() {
    case "$1" in
        "--version")
            echo "black, version 22.0.0"
            return 0
            ;;
        "--check")
            # Mock that files need formatting
            return 1
            ;;
        *)
            # Mock successful formatting
            return 0
            ;;
    esac
}

# Mock gh command
mock_gh() {
    case "$1" in
        "auth")
            return 0  # Always authenticated
            ;;
        "pr")
            case "$2" in
                "list")
                    # Return empty PR list
                    return 0
                    ;;
                "create")
                    echo "https://github.com/test/repo/pull/123"
                    return 0
                    ;;
                "edit")
                    echo "https://github.com/test/repo/pull/123"
                    return 0
                    ;;
            esac
            ;;
    esac
    return 0
}

# Test framework
test_count=0
pass_count=0
fail_count=0

run_mock_test() {
    local test_name="$1"
    local test_function="$2"
    
    test_count=$((test_count + 1))
    echo -e "${BLUE}Testing: $test_name${NC}"
    
    # Create isolated test environment
    local temp_dir
    temp_dir=$(mktemp -d -t brack_mock_test_XXXXXX)
    
    (
        cd "$temp_dir"
        
        # Override commands with mocks
        git() { mock_git "$@"; }
        black() { mock_black "$@"; }
        gh() { mock_gh "$@"; }
        
        # Export so subshells can use them
        export -f git black gh mock_git mock_black mock_gh
        
        # Source brack functions with mocked dependencies
        source "$BRACK_SCRIPT"
        
        # Initialize required global variables
        QUIET_MODE=false
        ORIGINAL_BRANCH="feature/test-branch"
        FORMATTING_BRANCH="feature/test-branch-auto-black-formatting"
        MERGE_BASE="def456abc123"
        EXISTING_FILES=()
        NEW_FILES=()
        STASH_CREATED=false
        declare -A BACKGROUND_PROCESSES
        ERROR_LOG="/tmp/test_error.log"
        BACKGROUND_ERROR_LOG="/tmp/test_bg_error.log"
        FILES_TO_FORMAT=()
        
        # Run the test
        "$test_function"
    )
    
    local result=$?
    rm -rf "$temp_dir"
    
    if [[ $result -eq 0 ]]; then
        echo -e "${GREEN}✓ PASS${NC}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}✗ FAIL${NC}"
        fail_count=$((fail_count + 1))
    fi
    echo
}

#=============================================================================
# MOCKED GIT OPERATION TESTS
#=============================================================================

test_validate_git_repository_mock() {
    if validate_git_repository; then
        return 0
    else
        echo "Git repository validation failed"
        return 1
    fi
}

test_get_current_branch_mock() {
    local branch
    branch=$(get_current_branch)
    if [[ "$branch" == "feature/test-branch" ]]; then
        return 0
    else
        echo "Expected 'feature/test-branch', got '$branch'"
        return 1
    fi
}

test_detect_main_branch_mock() {
    local main_branch
    if main_branch=$(find_main_branch); then
        echo "Detected main branch: $main_branch"
        return 0
    else
        echo "Failed to detect main branch"
        return 1
    fi
}

test_calculate_merge_base_mock() {
    local merge_base
    merge_base=$(calculate_merge_base "main")
    if [[ "$merge_base" == "def456abc123" ]]; then
        return 0
    else
        echo "Expected 'def456abc123', got '$merge_base'"
        return 1
    fi
}

test_check_file_existence_mock() {
    # Test existing file
    if check_file_existence_at_merge_base "def456abc123" "existing.py"; then
        echo "Correctly detected existing file"
    else
        echo "Failed to detect existing file"
        return 1
    fi
    
    # Test non-existing file
    if ! check_file_existence_at_merge_base "def456abc123" "nonexistent.py"; then
        echo "Correctly detected non-existing file"
        return 0
    else
        echo "Incorrectly detected non-existing file as existing"
        return 1
    fi
}

test_stash_operations_mock() {
    STASH_CREATED=false
    
    if save_working_directory; then
        echo "Stash operation completed"
        return 0
    else
        echo "Stash operation failed"
        return 1
    fi
}

test_branch_operations_mock() {
    local branch_name="feature/test-branch-auto-black-formatting"
    
    # Test branch creation
    if create_formatting_branch "$branch_name" "def456abc123"; then
        echo "Branch creation successful"
        return 0
    else
        echo "Branch creation failed"
        return 1
    fi
}

test_black_formatting_mock() {
    # Create test file
    echo "print( 'test' )" > test.py
    
    if check_black_availability; then
        echo "Black availability check passed"
    else
        echo "Black availability check failed"
        return 1
    fi
    
    FILES_TO_FORMAT=("test.py")
    if format_files_with_black; then
        echo "Black formatting completed"
        return 0
    else
        echo "Black formatting failed"
        return 1
    fi
}

test_commit_operations_mock() {
    # Create test file
    echo "print('formatted')" > formatted.py
    EXISTING_FILES=("formatted.py")
    
    if stage_formatted_files; then
        echo "File staging successful"
    else
        echo "File staging failed"
        return 1
    fi
    
    if create_formatting_commit; then
        echo "Commit creation successful"
        return 0
    else
        echo "Commit creation failed"  
        return 1
    fi
}

test_merge_operations_mock() {
    FORMATTING_BRANCH="feature/test-branch-auto-black-formatting"
    ORIGINAL_BRANCH="feature/test-branch"
    
    if merge_formatting_changes; then
        echo "Merge operation successful"
        return 0
    else
        echo "Merge operation failed"
        return 1
    fi
}

test_github_operations_mock() {
    if check_git_remote_origin; then
        echo "Remote origin check passed"
    else
        echo "Remote origin check failed"
        return 1
    fi
    
    if check_github_authentication; then
        echo "GitHub authentication check passed"
        return 0
    else
        echo "GitHub authentication check failed"
        return 1
    fi
}

#=============================================================================
# TEST EXECUTION
#=============================================================================

main() {
    echo -e "${BLUE}Brack Tool Mocked Git Operations Test Suite${NC}"
    echo "=============================================="
    echo
    
    run_mock_test "Git repository validation" test_validate_git_repository_mock
    run_mock_test "Current branch detection" test_get_current_branch_mock
    run_mock_test "Main branch detection" test_detect_main_branch_mock
    run_mock_test "Merge base calculation" test_calculate_merge_base_mock
    run_mock_test "File existence checking" test_check_file_existence_mock
    run_mock_test "Stash operations" test_stash_operations_mock
    run_mock_test "Branch operations" test_branch_operations_mock
    run_mock_test "Black formatting" test_black_formatting_mock
    run_mock_test "Commit operations" test_commit_operations_mock
    run_mock_test "Merge operations" test_merge_operations_mock
    run_mock_test "GitHub operations" test_github_operations_mock
    
    # Results
    echo "=============================================="
    echo -e "${BLUE}Mocked Git Operations Test Results${NC}"
    echo "Tests run: $test_count"
    echo -e "Passed: ${GREEN}$pass_count${NC}"
    echo -e "Failed: ${RED}$fail_count${NC}"
    
    if [[ $fail_count -eq 0 ]]; then
        echo -e "${GREEN}✓ All mocked operation tests passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Some mocked operation tests failed${NC}"
        return 1
    fi
}

main "$@"