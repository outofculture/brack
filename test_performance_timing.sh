#!/bin/bash
# Performance testing script to validate <1 second local operations requirement

set -e

echo "=== Performance Timing Tests ==="
echo "Target: Local operations must complete in <1 second"
echo

# Create test files for timing
echo "Setting up test files..."
mkdir -p test_timing
cat > test_timing/test1.py << 'EOF'
import os
import sys

def poorly_formatted_function(   ):
    x=1+2
    y   =   3   +   4
    z=(x+y)*2
    return z

if __name__=="__main__":
    print("hello world")
EOF

cat > test_timing/test2.py << 'EOF'
def another_function( a,b ,c):
    result=a+b+c
    return result


class   MyClass:
    def __init__( self ):
        self.value=42

    def method(self,param ):
        return self.value+param
EOF

cat > test_timing/test3.py << 'EOF'
from typing import List,Dict
import json

def process_data(data:List[Dict]):
    results=[]
    for item in data:
        processed={'id':item.get('id'),'value':item.get('value')*2}
        results.append(processed)
    return results
EOF

# Test 1: Clean working directory timing
echo "Test 1: Clean working directory performance"
git add test_timing/
git commit -m "Add test files for performance testing"

start_time=$(date +%s.%N)
timeout 5 ./brack test_timing/test1.py test_timing/test2.py test_timing/test3.py 2>/dev/null || true
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

echo "Clean directory execution time: ${duration}s"
if (( $(echo "$duration < 1.0" | bc -l) )); then
    echo "✅ PASS: Clean directory timing under 1 second"
else
    echo "❌ FAIL: Clean directory timing exceeded 1 second"
fi
echo

# Test 2: Dirty working directory timing (with stash operations)
echo "Test 2: Dirty working directory performance (with stashing)"

# Make working directory dirty
echo "# Modified file" >> test_timing/test1.py
echo "new_file = True" > test_timing/test4.py

start_time=$(date +%s.%N)
timeout 5 ./brack test_timing/test1.py test_timing/test2.py test_timing/test3.py 2>/dev/null || true
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

echo "Dirty directory execution time: ${duration}s"
if (( $(echo "$duration < 1.0" | bc -l) )); then
    echo "✅ PASS: Dirty directory timing under 1 second"
else
    echo "❌ FAIL: Dirty directory timing exceeded 1 second"
fi
echo

# Test 3: Multiple file timing (10 files)
echo "Test 3: Multiple file performance (10 files)"

# Create 10 test files
for i in {4..13}; do
    cat > test_timing/test${i}.py << EOF
def function_${i}():
    x   =   ${i}   +   1
    return x * 2

class Class${i}:
    def method(self,param):
        return param+${i}
EOF
done

git add test_timing/
git commit -m "Add more test files for performance testing"

start_time=$(date +%s.%N)
timeout 10 ./brack test_timing/*.py 2>/dev/null || true
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

echo "10-file execution time: ${duration}s"
if (( $(echo "$duration < 1.0" | bc -l) )); then
    echo "✅ PASS: 10-file timing under 1 second"
else
    echo "❌ FAIL: 10-file timing exceeded 1 second"
fi
echo

# Test 4: Individual operation timing breakdown
echo "Test 4: Operation breakdown timing"

# Time individual git operations
echo "Timing git operations..."
start_time=$(date +%s.%N)
git status --porcelain > /dev/null
end_time=$(date +%s.%N)
git_status_time=$(echo "$end_time - $start_time" | bc)
echo "git status: ${git_status_time}s"

start_time=$(date +%s.%N)
git merge-base HEAD main > /dev/null 2>&1 || git merge-base HEAD master > /dev/null 2>&1 || true
end_time=$(date +%s.%N)
merge_base_time=$(echo "$end_time - $start_time" | bc)
echo "git merge-base: ${merge_base_time}s"

start_time=$(date +%s.%N)
black --check test_timing/test1.py > /dev/null 2>&1 || true
end_time=$(date +%s.%N)
black_check_time=$(echo "$end_time - $start_time" | bc)
echo "black --check: ${black_check_time}s"

# Summary
echo
echo "=== Performance Test Summary ==="
echo "All tests should complete in <1 second for good user experience"
echo "Individual operation times:"
echo "  - git status: ${git_status_time}s"
echo "  - git merge-base: ${merge_base_time}s"  
echo "  - black --check: ${black_check_time}s"
echo

# Cleanup
echo "Cleaning up test files..."
git reset --hard HEAD~2
rm -rf test_timing/

echo "Performance timing tests completed!"