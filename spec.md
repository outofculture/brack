# Auto Black Formatter Tool Specification

## Overview

A command-line tool that applies `black` formatting to specified files and creates a separate PR for the formatting changes, while immediately merging those changes into the current working branch. This allows reviewers to see pure formatting changes in isolation while keeping the developer's feature branch clean and formatted.

## Goals

- Apply black formatting to files without polluting feature branch diffs
- Create separate PRs for formatting changes for reviewer clarity
- Complete local operations in <1 second (up to 10 seconds acceptable)
- Integrate cleanly with IDE workflows via custom commands/keybindings

## Usage

```bash
format-file path/to/file1.py [path/to/file2.py ...]
```

- Accepts one or more file paths as arguments
- All files are processed together in a single branch/PR

## Core Workflow

1. **Pre-flight check**: Check for existing `AUTO-BLACK-FORMATTING-ERROR` file and abort if found
2. **Stash changes**: `git stash` (save any uncommitted changes)
3. **Find parent commit**: Use `git merge-base HEAD main` to find the base commit
4. **Create formatting branch**: `git checkout -b {current-branch}-auto-black-formatting {merge-base-commit}`
5. **Handle missing files**: If any files don't exist at the merge-base commit, fall back to formatting them in the current branch (skip the separate PR workflow for those files)
6. **Apply formatting**: Run `black` on all specified files that exist at the merge-base
7. **Commit changes**: `git commit -m "black"`
8. **Background GitHub operations**: Fork process to handle:
   - `git push`
   - `gh pr create` (with graceful handling if PR already exists)
9. **Return to original branch**: `git checkout -`
10. **Merge formatting**: `git merge {current-branch}-auto-black-formatting`
11. **Restore changes**: `git stash pop`

## Branch Naming Strategy

- Format: `{current-branch-name}-auto-black-formatting`
- Example: `feature/user-auth` → `feature/user-auth-auto-black-formatting`
- Reuse existing formatting branches for the same base branch
- Multiple formatting operations on the same feature branch will update the existing formatting branch/PR

## Error Handling

### Black Formatting Failures
- If `black` fails on any file, immediately abort all operations
- Restore original state (checkout original branch, stash pop)
- Display black error output to user

### Merge Conflicts
- If `git merge` fails: restore original state (already on original branch, just `git stash pop`) and exit with error
- If `git stash pop` fails: leave user in conflict state to resolve manually

### Background GitHub Operation Failures
- Write error details to `AUTO-BLACK-FORMATTING-ERROR` file in repo root
- Include: full error message, command being run, branch name, directory context
- Future tool invocations check for this file and refuse to run until it's manually deleted
- Error message should prompt user to delete the file after investigating

### File Existence at Merge Base
- Files that don't exist at the merge-base commit are formatted in the current branch instead
- No separate PR is created for new files (avoids the noise problem since there's no existing formatting to change)

## Performance Considerations

- Fork GitHub operations (`git push` and `gh pr create`) to background after commit
- Target <1 second for local git operations
- Local operations complete before GitHub operations finish
- User gets formatted files immediately

## Implementation Notes

- Start with shell script implementation
- Consider compiled binary if performance is insufficient
- Handle nested repositories by operating on the innermost repository
- Gracefully handle existing PRs (don't create duplicates)

## Dependencies

- `git` command-line tool
- `black` Python formatter
- `gh` GitHub CLI tool
- Standard Unix shell utilities

## IDE Integration

- Designed to be invoked via custom IDE commands/keybindings
- Operates on currently open file(s)
- Silent success (only output on errors)

## Example Scenarios

### Successful Operation
```bash
$ format-file src/utils.py
# Local operations complete in ~200ms
# Background: pushing and creating PR
# User immediately has formatted file in working branch
```

### File Doesn't Exist at Merge Base
```bash
$ format-file src/new_feature.py
# Detects file is new, formats in current branch
# No separate PR created
# User gets formatted file locally
```

### Error with Recovery
```bash
$ format-file src/broken.py
# Black fails due to syntax error
# Tool restores original state
# User sees black error output
```

### Background Error Handling
```bash
$ format-file src/utils.py
# Local operations succeed
# Background push fails (network issue)
# Creates AUTO-BLACK-FORMATTING-ERROR file
$ format-file src/other.py
# Tool detects error file and refuses to run
# Prompts user to investigate and delete error file
```
