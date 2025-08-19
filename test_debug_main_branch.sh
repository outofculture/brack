#!/bin/bash
# Debug the main branch detection logic

set -e

echo "=== Debug Main Branch Detection ==="

./brack --cleanup >/dev/null 2>&1 || true

# Create completely isolated test repo
cd /tmp
rm -rf debug_main_branch
mkdir debug_main_branch
cd debug_main_branch

echo "Creating test repo without any main-like branches..."
git init >/dev/null
git config user.name "Test"
git config user.email "test@test.com"

# Create a branch that definitely isn't main/master/origin/main/origin/master
git checkout -b completely-different-branch >/dev/null

echo "def test(): pass" > test.py
git add test.py
git commit -m "test" >/dev/null

echo "Current repo state:"
echo "- Branch: $(git branch --show-current)"
echo "- All branches:"
git branch -a
echo "- Remotes:"
git remote -v || echo "No remotes"

echo
echo "Testing main branch detection directly..."
echo "Running: /home/martin/src/acq4/brack/brack test.py"
echo

# Run with verbose output and capture everything
/home/martin/src/acq4/brack/brack test.py 2>&1 | tee brack_output.log

echo
echo "Exit code: $?"

if [ -f AUTO-BLACK-FORMATTING-ERROR ]; then
    echo
    echo "Error file contents:"
    cat AUTO-BLACK-FORMATTING-ERROR
else
    echo "No error file was created"
fi

cd /home/martin/src/acq4/brack
rm -rf /tmp/debug_main_branch