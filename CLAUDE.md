# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**brack** is a command-line tool that applies black formatting to Python files while maintaining clean feature branch diffs. It creates separate PRs for formatting changes, allowing reviewers to see pure formatting changes in isolation while keeping the developer's feature branch clean and formatted.

## Key Architecture Components

### 1. Shell Script Foundation (`brack`)
- Main executable that orchestrates the entire workflow
- Handles command-line argument parsing and validation
- Coordinates git operations, black formatting, and GitHub integration
- Implements comprehensive error handling and rollback mechanisms

### 2. Git Workflow Management
- **Stashing System**: Safely preserves working directory changes during operations
- **Branch Management**: Creates temporary formatting branches from merge-base commits
- **Merge Operations**: Merges formatting changes back to feature branches with conflict detection
- **State Recovery**: Implements rollback mechanisms for failed operations

### 3. File Categorization System
- **Existing Files**: Files that exist at merge-base commit (formatted in separate branch/PR)
- **New Files**: Files created in current branch (formatted in-place, no separate PR)
- Uses `git show <commit>:<filepath>` to determine file existence at merge-base

### 4. GitHub Integration (Background Operations)
- **Push Operations**: Handles remote push with authentication and retry logic
- **PR Management**: Creates or updates PRs using GitHub CLI (`gh`)
- **Error Handling**: Logs failures to `AUTO-BLACK-FORMATTING-ERROR` file

### 5. Error Management System
- **Error State File**: `AUTO-BLACK-FORMATTING-ERROR` in repository root
- **Blocking Mechanism**: Tool refuses to run if error file exists from previous failures
- **Background Error Logging**: Captures GitHub operation failures for user review

## Development Workflow

### Core Branch Strategy
- Formatting branch naming: `{current-branch}-auto-black-formatting`
- Branches created from merge-base commit (`git merge-base HEAD main`)
- Reuses existing formatting branches for same feature branch
- Supports main/master/origin variants for base branch detection

### Performance Requirements
- **Local Operations**: Must complete in <1 second (target: ~200ms)
- **Background Operations**: GitHub push/PR creation runs asynchronously
- **User Experience**: User gets formatted files immediately, GitHub ops happen in background

### Error Recovery Patterns
1. **Git State Corruption**: Automatic rollback to original branch + stash restoration
2. **Black Formatting Failures**: Immediate abort with original state restoration
3. **Merge Conflicts**: Abort merge, restore stash, exit with error
4. **Background Failures**: Log to error file, block future operations until resolved

## Implementation Phases

The tool is designed for incremental implementation across 14 steps:

1. **Foundation** (Steps 1-3): Basic script, git detection, error state management
2. **Git Core** (Steps 4-6): Stashing, merge-base detection, file categorization
3. **Formatting** (Steps 7-10): Branch creation, black integration, commit/merge workflow
4. **GitHub Integration** (Steps 11-13): Background processes, push operations, PR creation
5. **Final Polish** (Step 14): Performance optimization, quiet mode, comprehensive testing

## Dependencies

### Required Tools
- `git` - Git version control operations
- `black` - Python code formatter
- `gh` - GitHub CLI for PR operations

### Environment Requirements
- Must be run from within a git repository
- Repository must have a main branch (main/master/origin variants)
- GitHub authentication must be configured for `gh` CLI

## Testing Strategy

### Critical Test Scenarios
- **Clean/Dirty Working Directory**: Test with and without uncommitted changes
- **File Categories**: Mix of existing files and new files
- **Branch States**: New formatting branches vs reusing existing ones
- **Error Conditions**: Black syntax errors, merge conflicts, network failures
- **GitHub Integration**: PR creation, updates, authentication failures

### Performance Validation
- Time local operations to ensure <1 second requirement
- Test with various file counts and sizes
- Validate background operation isolation

## Key Constraints

- **Safety First**: Never leave git repository in inconsistent state
- **No Force Operations**: Use `--force-with-lease` for safer force pushes
- **Clean Rollback**: All operations must be reversible on failure
- **User Experience**: Minimize blocking operations, clear error messages
- **IDE Integration**: Support quiet mode for editor integration

## Special Behaviors

### File Handling Logic
- Python files only (`.py` extension validation)
- Files existing at merge-base: formatted in separate branch/PR
- New files: formatted in current branch, no separate PR
- Handles file paths with spaces properly

### Branch Management
- Automatically detects main branch variants (main, master, origin/main, origin/master)
- Reuses existing formatting branches to update PRs rather than create duplicates
- Cleans up formatting branches after successful merge

### Background Operations
- Forks GitHub operations to prevent blocking user
- Comprehensive error logging for debugging background failures
- Process management ensures proper cleanup on script termination