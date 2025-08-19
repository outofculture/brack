#!/bin/bash
# Comprehensive error scenario testing

set -e

echo "=== Error Scenario Tests ==="
echo

# Test 1: No main branch
echo "Test 1: No main branch detection"
cd /tmp
rm -rf test_no_main
mkdir test_no_main
cd test_no_main
git init >/dev/null
git config user.name "Test User"
git config user.email "test@test.com"
git checkout -b feature >/dev/null

echo "def test(): pass" > test.py
git add test.py
git commit -m "test commit" >/dev/null

echo "Running brack (first time - should create error)..."
/home/martin/src/acq4/brack/brack test.py >/dev/null 2>&1 || true

echo "Running brack (second time - should show error)..."
ERROR_OUTPUT=$(/home/martin/src/acq4/brack/brack test.py 2>&1 || true)

if echo "$ERROR_OUTPUT" | grep -q "No main branch found"; then
    echo "✅ PASS: No main branch error properly detected"
else
    echo "❌ FAIL: No main branch error not detected"
    echo "Actual error: $ERROR_OUTPUT"
fi

cd /home/martin/src/acq4/brack
rm -rf /tmp/test_no_main
echo

# Test 2: Detached HEAD
echo "Test 2: Detached HEAD detection"

echo "def test(): pass" > test_detached.py
git add test_detached.py
git commit -m "Test commit" >/dev/null

# Enter detached HEAD
COMMIT_HASH=$(git rev-parse HEAD)
git checkout $COMMIT_HASH >/dev/null 2>&1

echo "Running brack in detached HEAD state..."
DETACHED_OUTPUT=$(./brack test_detached.py 2>&1 || true)

if echo "$DETACHED_OUTPUT" | grep -q "Cannot run on detached HEAD"; then
    echo "✅ PASS: Detached HEAD properly rejected"
else
    echo "❌ FAIL: Detached HEAD not properly rejected"
    echo "Actual output: $DETACHED_OUTPUT"
fi

# Return to branch and clean up
git checkout feature/test-error-recovery >/dev/null 2>&1
git reset --hard HEAD~1 >/dev/null 2>&1
rm -f test_detached.py
echo

# Test 3: Non-existent files
echo "Test 3: Non-existent file handling"
NONEXIST_OUTPUT=$(./brack nonexistent.py 2>&1 || true)

if echo "$NONEXIST_OUTPUT" | grep -q "does not exist"; then
    echo "✅ PASS: Non-existent file properly rejected"
else
    echo "❌ FAIL: Non-existent file not properly rejected"
    echo "Actual output: $NONEXIST_OUTPUT"
fi
echo

# Test 4: Non-Python files
echo "Test 4: Non-Python file handling"
echo "test content" > test.txt
NONPYTHON_OUTPUT=$(./brack test.txt 2>&1 || true)

if echo "$NONPYTHON_OUTPUT" | grep -q "not.*Python.*file"; then
    echo "✅ PASS: Non-Python file properly rejected"
else
    echo "❌ FAIL: Non-Python file not properly rejected"
    echo "Actual output: $NONPYTHON_OUTPUT"
fi

rm -f test.txt
echo

# Test 5: Non-git repository
echo "Test 5: Non-git repository detection"
cd /tmp
mkdir test_not_git
cd test_not_git
echo "def test(): pass" > test.py

NOTGIT_OUTPUT=$(/home/martin/src/acq4/brack/brack test.py 2>&1 || true)

if echo "$NOTGIT_OUTPUT" | grep -q -i "git.*repository\|not.*git"; then
    echo "✅ PASS: Non-git directory properly rejected"
else
    echo "❌ FAIL: Non-git directory not properly rejected"
    echo "Actual output: $NOTGIT_OUTPUT"
fi

cd /home/martin/src/acq4/brack
rm -rf /tmp/test_not_git
echo

echo "=== Error Scenario Test Summary ==="
echo "Tested critical error conditions that brack should handle gracefully"
echo "All tests verify that appropriate error messages are displayed"