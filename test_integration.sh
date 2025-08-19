#!/bin/bash

# Integration tests for brack tool
# Tests complete end-to-end workflows with real git operations

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRACK_SCRIPT="$SCRIPT_DIR/brack"
ORIGINAL_PWD="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

test_count=0
pass_count=0
fail_count=0

# Create test environment
setup_test_repo() {
    local repo_name="$1"
    local temp_dir
    temp_dir=$(mktemp -d -t "brack_integration_${repo_name}_XXXXXX")
    
    cd "$temp_dir"
    
    # Initialize git repository
    git init --quiet
    git config user.name "Integration Test"
    git config user.email "test@brack-integration.com"
    
    # Create initial commit
    echo "# Integration Test Repository" > README.md
    git add README.md
    git commit -m "Initial commit" --quiet
    
    # Ensure we have main branch
    git checkout -b main --quiet 2>/dev/null || git branch -M main --quiet
    
    # Add some initial Python files
    cat > existing_file.py << 'EOF'
def hello_world():
    print("Hello, World!")
    
def add_numbers(a,b):
    return a+b
    
class TestClass:
    def __init__(self,name):
        self.name=name
    
    def get_name(self):
        return self.name
EOF
    
    git add existing_file.py
    git commit -m "Add existing Python file" --quiet
    
    echo "$temp_dir"
}

cleanup_test_repo() {
    local temp_dir="$1"
    cd "$ORIGINAL_PWD"
    rm -rf "$temp_dir"
}

run_integration_test() {
    local test_name="$1"
    local test_function="$2"
    
    test_count=$((test_count + 1))
    echo -e "${BLUE}Integration Test: $test_name${NC}"
    
    if "$test_function"; then
        echo -e "${GREEN}✓ PASS${NC}"
        pass_count=$((pass_count + 1))
    else
        echo -e "${RED}✗ FAIL${NC}"
        fail_count=$((fail_count + 1))
    fi
    echo
}

# Mock external dependencies for safe testing
setup_mocks() {
    # Mock black command to avoid dependency
    black() {
        case "$1" in
            "--version")
                echo "black, version 22.0.0"
                return 0
                ;;
            "--check")
                # Simulate that files need formatting
                return 1
                ;;
            *)
                # Simulate successful formatting by actually reformatting the files
                for file in "$@"; do
                    if [[ -f "$file" ]]; then
                        # Simple reformatting simulation
                        python3 -c "
import sys
with open('$file', 'r') as f:
    content = f.read()
# Simple formatting changes
content = content.replace('def hello_world():', 'def hello_world():')
content = content.replace('print(\"Hello, World!\")', 'print(\"Hello, World!\")')
content = content.replace('def add_numbers(a,b):', 'def add_numbers(a, b):')
content = content.replace('return a+b', 'return a + b')
content = content.replace('def __init__(self,name):', 'def __init__(self, name):')
content = content.replace('self.name=name', 'self.name = name')
with open('$file', 'w') as f:
    f.write(content)
" 2>/dev/null || return 0
                    fi
                done
                return 0
                ;;
        esac
    }
    
    # Mock gh command to avoid GitHub dependency
    gh() {
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
                        echo "https://github.com/test/integration-repo/pull/123"
                        return 0
                        ;;
                    "edit")
                        echo "https://github.com/test/integration-repo/pull/123"
                        return 0
                        ;;
                esac
                ;;
        esac
        return 0
    }
    
    # Export mocks so subprocesses can use them
    export -f black gh
}

#=============================================================================
# INTEGRATION TESTS
#=============================================================================

test_complete_workflow_existing_files() {
    local test_repo
    test_repo=$(setup_test_repo "existing_files")
    
    # Create feature branch with modifications
    git checkout -b feature/test-existing-files --quiet
    
    # Modify the existing file to need formatting
    cat >> existing_file.py << 'EOF'

def new_function(param1,param2,param3):
    result=param1+param2*param3
    if result>100:
        return "large"
    else:
        return "small"
EOF
    
    git add existing_file.py
    git commit -m "Add new function needing formatting" --quiet
    
    # Run brack on existing file
    if timeout 30 "$BRACK_SCRIPT" --quiet existing_file.py 2>/dev/null; then
        echo "Brack completed successfully"
        
        # Check that we're still on the feature branch
        local current_branch
        current_branch=$(git branch --show-current)
        if [[ "$current_branch" == "feature/test-existing-files" ]]; then
            echo "✓ Remained on feature branch"
        else
            echo "✗ Not on expected feature branch: $current_branch"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        # Check that formatting branch was created and merged
        if git log --oneline | grep -q "Merge formatting changes"; then
            echo "✓ Formatting changes were merged"
        else
            echo "✗ No formatting merge found in git log"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        # Check that the file was actually formatted
        if grep -q "def new_function(param1, param2, param3):" existing_file.py; then
            echo "✓ File was formatted correctly"
        else
            echo "✗ File was not formatted as expected"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        cleanup_test_repo "$test_repo"
        return 0
    else
        echo "✗ Brack execution failed"
        cleanup_test_repo "$test_repo"
        return 1
    fi
}

test_complete_workflow_new_files() {
    local test_repo
    test_repo=$(setup_test_repo "new_files")
    
    # Create feature branch
    git checkout -b feature/test-new-files --quiet
    
    # Add a new Python file that needs formatting
    cat > new_file.py << 'EOF'
def process_data(data_list,filter_func,transform_func):
    filtered_data=[]
    for item in data_list:
        if filter_func(item):
            transformed=transform_func(item)
            filtered_data.append(transformed)
    return filtered_data

class DataProcessor:
    def __init__(self,config):
        self.config=config
        self.results=[]
    
    def process(self,data):
        for item in data:
            if self.validate(item):
                processed=self.transform(item)
                self.results.append(processed)
EOF
    
    # Don't commit the new file yet - it shouldn't exist at merge-base
    
    # Run brack on new file
    if timeout 30 "$BRACK_SCRIPT" --quiet new_file.py 2>/dev/null; then
        echo "Brack completed successfully for new file"
        
        # Check that file was formatted in place (no separate branch needed)
        if grep -q "def process_data(data_list, filter_func, transform_func):" new_file.py; then
            echo "✓ New file was formatted correctly in current branch"
        else
            echo "✗ New file was not formatted as expected"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        # Check that no formatting branch merge occurred (since it's a new file)
        if ! git log --oneline | grep -q "Merge formatting changes"; then
            echo "✓ No formatting branch merge for new file (correct behavior)"
        else
            echo "✗ Unexpected formatting branch merge for new file"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        cleanup_test_repo "$test_repo"
        return 0
    else
        echo "✗ Brack execution failed for new file"
        cleanup_test_repo "$test_repo"
        return 1
    fi
}

test_complete_workflow_mixed_files() {
    local test_repo
    test_repo=$(setup_test_repo "mixed_files")
    
    # Create feature branch
    git checkout -b feature/test-mixed-files --quiet
    
    # Modify existing file
    echo "
def modified_existing_function(a,b,c):
    return a+b+c" >> existing_file.py
    
    # Add new file
    cat > brand_new_file.py << 'EOF'
def utility_function(x,y):
    return x*y+1

class Helper:
    def __init__(self,value):
        self.value=value
EOF
    
    git add existing_file.py
    git commit -m "Modify existing file" --quiet
    
    # Run brack on both files
    if timeout 30 "$BRACK_SCRIPT" --quiet existing_file.py brand_new_file.py 2>/dev/null; then
        echo "Brack completed successfully for mixed files"
        
        # Check formatting of both files
        if grep -q "def modified_existing_function(a, b, c):" existing_file.py; then
            echo "✓ Existing file was formatted correctly"
        else
            echo "✗ Existing file was not formatted as expected"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        if grep -q "def utility_function(x, y):" brand_new_file.py; then
            echo "✓ New file was formatted correctly"
        else
            echo "✗ New file was not formatted as expected"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        # Should have formatting branch merge for existing file
        if git log --oneline | grep -q "Merge formatting changes"; then
            echo "✓ Formatting branch merge occurred for existing file"
        else
            echo "✗ No formatting branch merge found"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        cleanup_test_repo "$test_repo"
        return 0
    else
        echo "✗ Brack execution failed for mixed files"
        cleanup_test_repo "$test_repo"
        return 1
    fi
}

test_workflow_with_uncommitted_changes() {
    local test_repo
    test_repo=$(setup_test_repo "uncommitted_changes")
    
    # Create feature branch
    git checkout -b feature/test-uncommitted --quiet
    
    # Create uncommitted changes
    echo "# Uncommitted change" >> README.md
    cat > uncommitted_file.py << 'EOF'
def uncommitted_function():
    print("This is uncommitted")
EOF
    
    # Modify existing file for formatting (and commit it)
    echo "
def committed_function(a,b):
    return a*b" >> existing_file.py
    
    git add existing_file.py
    git commit -m "Add function needing formatting" --quiet
    
    # Now run brack - it should handle uncommitted changes
    if timeout 30 "$BRACK_SCRIPT" --quiet existing_file.py 2>/dev/null; then
        echo "Brack completed with uncommitted changes present"
        
        # Check that uncommitted changes are still present
        if [[ -f "uncommitted_file.py" ]] && git status --porcelain | grep -q "uncommitted_file.py"; then
            echo "✓ Uncommitted changes were preserved"
        else
            echo "✗ Uncommitted changes were lost"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        # Check that committed file was formatted
        if grep -q "def committed_function(a, b):" existing_file.py; then
            echo "✓ Committed file was formatted correctly"
        else
            echo "✗ Committed file was not formatted"
            cleanup_test_repo "$test_repo"
            return 1
        fi
        
        cleanup_test_repo "$test_repo"
        return 0
    else
        echo "✗ Brack execution failed with uncommitted changes"
        cleanup_test_repo "$test_repo"
        return 1
    fi
}

test_workflow_error_recovery() {
    local test_repo
    test_repo=$(setup_test_repo "error_recovery")
    
    # Create feature branch
    git checkout -b feature/test-error-recovery --quiet
    
    # Create error state file to test recovery
    echo "Test error state" > AUTO-BLACK-FORMATTING-ERROR
    
    # Try to run brack - should be blocked
    if ! "$BRACK_SCRIPT" --quiet existing_file.py 2>/dev/null; then
        echo "✓ Brack correctly blocked by error state"
    else
        echo "✗ Brack should have been blocked by error state"
        cleanup_test_repo "$test_repo"
        return 1
    fi
    
    # Test cleanup
    if "$BRACK_SCRIPT" --cleanup 2>/dev/null; then
        echo "✓ Error state cleanup successful"
    else
        echo "✗ Error state cleanup failed"
        cleanup_test_repo "$test_repo"
        return 1
    fi
    
    # Now brack should work
    echo "
def error_recovery_test(x,y):
    return x+y" >> existing_file.py
    
    git add existing_file.py
    git commit -m "Add function for error recovery test" --quiet
    
    if timeout 30 "$BRACK_SCRIPT" --quiet existing_file.py 2>/dev/null; then
        echo "✓ Brack works after error state cleanup"
        cleanup_test_repo "$test_repo"
        return 0
    else
        echo "✗ Brack still failed after error state cleanup"
        cleanup_test_repo "$test_repo"
        return 1
    fi
}

#=============================================================================
# TEST EXECUTION
#=============================================================================

main() {
    echo -e "${BLUE}Brack Tool Integration Test Suite${NC}"
    echo "========================================"
    echo
    
    cd "$SCRIPT_DIR"
    
    # Setup mocks for safe testing
    setup_mocks
    
    # Run integration tests
    run_integration_test "Complete workflow - existing files" test_complete_workflow_existing_files
    run_integration_test "Complete workflow - new files" test_complete_workflow_new_files  
    run_integration_test "Complete workflow - mixed files" test_complete_workflow_mixed_files
    run_integration_test "Workflow with uncommitted changes" test_workflow_with_uncommitted_changes
    run_integration_test "Workflow error recovery" test_workflow_error_recovery
    
    # Results
    echo "========================================"
    echo -e "${BLUE}Integration Test Results${NC}"
    echo "Tests run: $test_count"
    echo -e "Passed: ${GREEN}$pass_count${NC}"
    echo -e "Failed: ${RED}$fail_count${NC}"
    
    if [[ $fail_count -eq 0 ]]; then
        echo -e "${GREEN}✓ All integration tests passed!${NC}"
        echo -e "${GREEN}End-to-end workflows are functioning correctly.${NC}"
        return 0
    else
        echo -e "${RED}✗ Some integration tests failed${NC}"
        echo -e "${RED}Review workflow implementations.${NC}"
        return 1
    fi
}

main "$@"