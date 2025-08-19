#!/bin/bash
# Simple test for git error scenarios

set -e

echo "=== Simple Git Error Tests ==="

# Test 1: Missing main branch simulation
echo "Test 1: Missing main branch scenario"

# Create a temporary git repo to test with
mkdir -p /tmp/test_repo_no_main
cd /tmp/test_repo_no_main
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Create a file and commit on 'develop' branch (no main/master)
git checkout -b develop
echo "def test(): pass" > test.py
git add test.py
git commit -m "Initial commit on develop"

# Test brack tool (should fail due to missing main branch)
/home/martin/src/acq4/brack/brack test.py 2>&1 | grep -q "No main branch found" && echo "✅ PASS: Missing main branch properly detected" || echo "❌ FAIL: Missing main branch not detected"

cd /home/martin/src/acq4/brack
rm -rf /tmp/test_repo_no_main

# Test 2: Detached HEAD 
echo "Test 2: Detached HEAD state"

# Create test commit
echo "def test(): pass" > test_detached.py
git add test_detached.py
git commit -m "Test commit for detached HEAD"

# Enter detached HEAD state
COMMIT_HASH=$(git rev-parse HEAD)
git checkout $COMMIT_HASH > /dev/null 2>&1

# Test (should fail)
./brack test_detached.py 2>&1 | grep -q "Cannot run on detached HEAD" && echo "✅ PASS: Detached HEAD properly rejected" || echo "❌ FAIL: Detached HEAD not rejected"

# Return to branch and clean up
git checkout feature/test-error-recovery > /dev/null 2>&1
git reset --hard HEAD~1 > /dev/null 2>&1

echo "Simple git error tests completed!"