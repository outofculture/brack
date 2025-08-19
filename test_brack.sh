#!/bin/bash

# Comprehensive unit test framework for brack tool
# Tests each function independently with mocked dependencies

set -euo pipefail

# Test framework setup
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRACK_SCRIPT="$TEST_DIR/brack"
TEST_TEMP_DIR=""
ORIGINAL_PWD="$(pwd)"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
CURRENT_TEST=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test utilities
setup_test_environment() {
    TEST_TEMP_DIR=$(mktemp -d -t brack_test_XXXXXX)
    cd "$TEST_TEMP_DIR"
    
    # Create a mock git repository
    git init --quiet
    git config user.name "Test User"
    git config user.email "test@example.com"
    
    # Create initial commit
    echo "# Test Repository" > README.md
    git add README.md
    git commit -m "Initial commit" --quiet
    
    # Create main branch (some repos use master by default)
    git checkout -b main --quiet 2>/dev/null || git branch -M main --quiet
}

teardown_test_environment() {
    cd "$ORIGINAL_PWD"
    if [[ -n "$TEST_TEMP_DIR" && -d "$TEST_TEMP_DIR" ]]; then
        rm -rf "$TEST_TEMP_DIR"
    fi
}

# Test assertion functions
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-}"
    
    if [[ "$expected" == "$actual" ]]; then
        return 0
    else
        echo -e "${RED}ASSERTION FAILED${NC}: $message"
        echo -e "  Expected: ${GREEN}$expected${NC}"
        echo -e "  Actual:   ${RED}$actual${NC}"
        return 1
    fi
}

assert_not_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-}"
    
    if [[ "$expected" != "$actual" ]]; then
        return 0
    else
        echo -e "${RED}ASSERTION FAILED${NC}: $message"
        echo -e "  Expected NOT: ${RED}$expected${NC}"
        echo -e "  Actual:       ${RED}$actual${NC}"
        return 1
    fi
}

assert_true() {
    local condition="$1"
    local message="${2:-}"
    
    # Evaluate the condition if it looks like a test expression
    local result
    if [[ "$condition" =~ ^\[\[ ]]; then
        if eval "$condition"; then
            result="true"
        else
            result="false"
        fi
    else
        result="$condition"
    fi
    
    if [[ "$result" == "true" || "$result" == "0" ]]; then
        return 0
    else
        echo -e "${RED}ASSERTION FAILED${NC}: $message"
        echo -e "  Expected: ${GREEN}true${NC}"
        echo -e "  Condition: ${RED}$condition${NC}"
        return 1
    fi
}

assert_false() {
    local condition="$1"
    local message="${2:-}"
    
    if [[ "$condition" == "false" || "$condition" != "0" ]]; then
        return 0
    else
        echo -e "${RED}ASSERTION FAILED${NC}: $message"
        echo -e "  Expected: ${GREEN}false${NC}"
        echo -e "  Actual:   ${RED}$condition${NC}"
        return 1
    fi
}

assert_file_exists() {
    local file="$1"
    local message="${2:-File should exist: $file}"
    
    if [[ -f "$file" ]]; then
        return 0
    else
        echo -e "${RED}ASSERTION FAILED${NC}: $message"
        return 1
    fi
}

assert_file_not_exists() {
    local file="$1"
    local message="${2:-File should not exist: $file}"
    
    if [[ ! -f "$file" ]]; then
        return 0
    else
        echo -e "${RED}ASSERTION FAILED${NC}: $message"
        return 1
    fi
}

# Test execution framework
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    CURRENT_TEST="$test_name"
    TESTS_RUN=$((TESTS_RUN + 1))
    
    echo -e "${BLUE}Running test:${NC} $test_name"
    
    # Setup clean environment for each test
    setup_test_environment
    
    # Source brack script functions in a subshell to avoid global state contamination
    if (
        # Mock global variables to prevent undefined variable errors
        QUIET_MODE=false
        ORIGINAL_BRANCH=""
        FORMATTING_BRANCH=""
        MERGE_BASE=""
        EXISTING_FILES=()
        NEW_FILES=()
        STASH_CREATED=false
        declare -A BACKGROUND_PROCESSES
        ERROR_LOG=""
        BACKGROUND_ERROR_LOG=""
        
        # Source the brack script (functions only, not execution)
        source "$BRACK_SCRIPT"
        
        # Run the test function
        "$test_function"
    ); then
        echo -e "${GREEN}✓ PASSED:${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAILED:${NC} $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    
    teardown_test_environment
    echo ""
}

# Mock functions to replace external dependencies
setup_mocks() {
    # Mock git commands that might not work in test environment
    git() {
        case "$1" in
            "rev-parse")
                if [[ "$2" == "--git-dir" ]]; then
                    echo ".git"
                    return 0
                elif [[ "$2" == "--show-toplevel" ]]; then
                    echo "$TEST_TEMP_DIR"
                    return 0
                fi
                ;;
            "branch")
                if [[ "$2" == "--show-current" ]]; then
                    echo "test-branch"
                    return 0
                fi
                ;;
            "status")
                if [[ "$2" == "--porcelain" ]]; then
                    # Return empty for clean working directory
                    return 0
                fi
                ;;
        esac
        # Fall through to real git for other operations
        command git "$@"
    }
    
    # Mock black command
    black() {
        case "$1" in
            "--version")
                echo "black, 22.0.0"
                return 0
                ;;
            *)
                # Mock successful formatting
                return 0
                ;;
        esac
    }
    
    # Mock gh command
    gh() {
        case "$1" in
            "auth")
                return 0  # Assume authenticated
                ;;
            "pr")
                case "$2" in
                    "list")
                        # Return empty PR list
                        return 0
                        ;;
                    "create"|"edit")
                        echo "https://github.com/test/repo/pull/123"
                        return 0
                        ;;
                esac
                ;;
        esac
        return 0
    }
}

#=============================================================================
# UNIT TESTS - Logging Functions
#=============================================================================

test_log_info() {
    local output
    output=$(log_info "Test message" 2>&1)
    # Strip ANSI color codes for comparison
    output=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
    assert_equals "[INFO] Test message" "$output" "log_info should format message correctly"
}

test_log_warn() {
    local output
    output=$(log_warn "Warning message" 2>&1)
    # Strip ANSI color codes for comparison
    output=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
    assert_equals "[WARN] Warning message" "$output" "log_warn should format message correctly"
}

test_log_error() {
    local output
    output=$(log_error "Error message" 2>&1)
    # Strip ANSI color codes for comparison
    output=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
    assert_equals "[ERROR] Error message" "$output" "log_error should format message correctly"
}

test_log_success() {
    local output
    output=$(log_success "Success message" 2>&1)
    # Strip ANSI color codes for comparison
    output=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
    assert_equals "[SUCCESS] Success message" "$output" "log_success should format message correctly"
}

#=============================================================================
# UNIT TESTS - Argument Parsing
#=============================================================================

test_parse_arguments_help() {
    # Test help flag detection - capture exit behavior
    local help_output
    help_output=$(parse_arguments --help 2>&1 || true)
    assert_true "[[ '$help_output' =~ 'USAGE:' ]]" "Help should display usage information"
}

test_parse_arguments_quiet() {
    # Create dummy files for testing
    touch test.py
    QUIET_MODE=false
    FILES_TO_FORMAT=()
    parse_arguments --quiet test.py 2>/dev/null || true
    assert_equals "true" "$QUIET_MODE" "Quiet mode should be enabled"
}

test_parse_arguments_files() {
    # Create dummy files for testing
    touch file1.py file2.py
    FILES_TO_FORMAT=()
    QUIET_MODE=false
    parse_arguments file1.py file2.py 2>/dev/null || true
    assert_equals "2" "${#FILES_TO_FORMAT[@]}" "Should parse multiple files"
    assert_equals "file1.py" "${FILES_TO_FORMAT[0]}" "First file should be correct"
    assert_equals "file2.py" "${FILES_TO_FORMAT[1]}" "Second file should be correct"
}

#=============================================================================
# UNIT TESTS - Git Repository Detection
#=============================================================================

test_validate_git_repository() {
    # Should succeed in our test git repo
    if validate_git_repository 2>/dev/null; then
        assert_true "true" "Should detect git repository"
    else
        assert_true "false" "Failed to detect git repository"
    fi
}

test_get_current_branch() {
    local branch
    branch=$(get_current_branch)
    assert_not_equals "" "$branch" "Should return current branch name"
}

test_validate_not_detached_head() {
    # Should succeed on a normal branch
    if validate_not_detached_head 2>/dev/null; then
        assert_true "true" "Should not be on detached HEAD"
    else
        assert_true "false" "Should not detect detached HEAD on normal branch"
    fi
}

#=============================================================================
# UNIT TESTS - Error State Management
#=============================================================================

test_create_error_state() {
    local error_file="AUTO-BLACK-FORMATTING-ERROR"
    
    # Clean up any existing error file
    rm -f "$error_file"
    
    create_error_state "Test error" "test command"
    
    assert_file_exists "$error_file" "Error state file should be created"
    
    local content
    content=$(cat "$error_file")
    assert_true "[[ '$content' =~ 'Test error' ]]" "Error file should contain error message"
    assert_true "[[ '$content' =~ 'test command' ]]" "Error file should contain command"
}

test_check_error_state_clean() {
    local error_file="AUTO-BLACK-FORMATTING-ERROR"
    rm -f "$error_file"
    
    if check_error_state 2>/dev/null; then
        assert_true "true" "Should pass when no error file exists"
    else
        assert_true "false" "Should not fail when no error state exists"
    fi
}

test_cleanup_error_state() {
    local error_file="AUTO-BLACK-FORMATTING-ERROR"
    
    # Create error file
    echo "Test error" > "$error_file"
    assert_file_exists "$error_file" "Error file should exist before cleanup"
    
    cleanup_error_state
    assert_file_not_exists "$error_file" "Error file should be removed after cleanup"
}

#=============================================================================
# UNIT TESTS - File Operations
#=============================================================================

test_discover_python_files() {
    # Create test Python files
    touch test1.py test2.py test3.txt
    
    # Set global variable that discover_python_files expects
    FILES_TO_FORMAT=("test1.py" "test2.py" "test3.txt")
    
    # Call the function which modifies FILES_TO_FORMAT in place
    discover_python_files 2>/dev/null || true
    
    assert_equals "2" "${#FILES_TO_FORMAT[@]}" "Should filter to Python files only"
    assert_equals "test1.py" "${FILES_TO_FORMAT[0]}" "First Python file should be included"
    assert_equals "test2.py" "${FILES_TO_FORMAT[1]}" "Second Python file should be included"
}

test_generate_formatting_branch_name() {
    ORIGINAL_BRANCH="feature/awesome-feature"
    local branch_name
    branch_name=$(generate_formatting_branch_name)
    assert_equals "feature/awesome-feature-auto-black-formatting" "$branch_name" "Should generate correct branch name"
}

#=============================================================================
# UNIT TESTS - Performance Functions
#=============================================================================

test_get_timestamp_ms() {
    local timestamp
    timestamp=$(get_timestamp_ms)
    assert_true "[[ '$timestamp' =~ ^[0-9]+$ ]]" "Timestamp should be numeric"
    assert_true "[[ ${#timestamp} -ge 10 ]]" "Timestamp should have reasonable length"
}

test_calculate_duration() {
    local start=1000000
    local end=1002000
    local duration
    duration=$(calculate_duration $start $end)
    assert_equals "2000" "$duration" "Duration calculation should be correct"
}

test_validate_performance_timing() {
    local start=1000000
    local end=1000500  # 500ms duration
    
    if validate_performance_timing $start $end 2>/dev/null; then
        assert_true "true" "Should pass for duration under 1000ms"
    else
        assert_true "false" "Performance validation failed unexpectedly"
    fi
    
    local long_end=1002000  # 2000ms duration
    if validate_performance_timing $start $long_end 2>/dev/null; then
        assert_true "false" "Should fail for duration over 1000ms"
    else
        assert_true "true" "Should fail for duration over 1000ms"
    fi
}

#=============================================================================
# UNIT TESTS - Background Process Management
#=============================================================================

test_start_background_process() {
    # Create a simple test function
    test_background_func() {
        sleep 0.1
        echo "Background task completed"
    }
    
    declare -A BACKGROUND_PROCESSES
    BACKGROUND_ERROR_LOG="/tmp/test_bg_error.log"
    
    start_background_process "test_process" "test_background_func"
    
    # Check that process was started
    assert_true "[[ -n '${BACKGROUND_PROCESSES[test_process]:-}' ]]" "Background process should be tracked"
    
    # Wait for process to complete
    wait "${BACKGROUND_PROCESSES[test_process]}" 2>/dev/null || true
    
    # Cleanup
    rm -f "$BACKGROUND_ERROR_LOG"
}

#=============================================================================
# TEST EXECUTION
#=============================================================================

main() {
    echo -e "${BLUE}Brack Tool Unit Test Suite${NC}"
    echo "========================================="
    echo ""
    
    # Setup mocks
    setup_mocks
    
    # Run all tests
    echo -e "${YELLOW}Testing Logging Functions${NC}"
    run_test "log_info formatting" test_log_info
    run_test "log_warn formatting" test_log_warn
    run_test "log_error formatting" test_log_error
    run_test "log_success formatting" test_log_success
    
    echo -e "${YELLOW}Testing Argument Parsing${NC}"
    run_test "parse_arguments help flags" test_parse_arguments_help
    run_test "parse_arguments quiet flags" test_parse_arguments_quiet
    run_test "parse_arguments file list" test_parse_arguments_files
    
    echo -e "${YELLOW}Testing Git Repository Detection${NC}"
    run_test "validate_git_repository" test_validate_git_repository
    run_test "get_current_branch" test_get_current_branch
    run_test "validate_not_detached_head" test_validate_not_detached_head
    
    echo -e "${YELLOW}Testing Error State Management${NC}"
    run_test "create_error_state" test_create_error_state
    run_test "check_error_state clean" test_check_error_state_clean
    run_test "cleanup_error_state" test_cleanup_error_state
    
    echo -e "${YELLOW}Testing File Operations${NC}"
    run_test "discover_python_files" test_discover_python_files
    run_test "generate_formatting_branch_name" test_generate_formatting_branch_name
    
    echo -e "${YELLOW}Testing Performance Functions${NC}"
    run_test "get_timestamp_ms" test_get_timestamp_ms
    run_test "calculate_duration" test_calculate_duration
    run_test "validate_performance_timing" test_validate_performance_timing
    
    echo -e "${YELLOW}Testing Background Process Management${NC}"
    run_test "start_background_process" test_start_background_process
    
    # Print results
    echo "========================================="
    echo -e "${BLUE}Test Results${NC}"
    echo "Tests run: $TESTS_RUN"
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed.${NC}"
        return 1
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi