# Auto Black Formatter Tool - Development Plan

## Project Overview

This project implements a command-line tool called `brack` that applies black formatting to Python files while creating separate PRs for the formatting changes. The tool maintains clean feature branch diffs by isolating formatting changes into dedicated branches and PRs.

## Architecture Components

### 1. Core Shell Script (`brack`)
- Main executable that orchestrates the entire workflow
- Handles command-line argument parsing
- Coordinates all git operations and black formatting
- Implements error handling and recovery mechanisms

### 2. Git Workflow Manager
- Manages branch creation, switching, and cleanup
- Handles merge operations and conflict detection
- Implements safe stashing and restoration of changes
- Tracks merge-base commit detection

### 3. Black Formatting Engine
- Validates files can be formatted before proceeding
- Applies black formatting to specified files
- Handles formatting errors and provides user feedback
- Manages file existence checks at different commits

### 4. GitHub Integration
- Handles background push operations
- Creates and manages PRs via GitHub CLI
- Implements graceful handling of existing PRs
- Manages error logging for background operations

### 5. Error Management System
- Creates and monitors error state files
- Implements rollback mechanisms for failed operations
- Provides clear user feedback on failures
- Handles various failure scenarios (merge conflicts, network issues, etc.)

## Refined Implementation Steps

### Step 1: Basic Shell Script Foundation
**Goal**: Create executable script with argument parsing

**Tasks**:
- Create executable `brack` shell script with shebang
- Implement basic command-line argument parsing (files list)
- Add help message and usage information
- Add basic error output and exit codes

### Step 2: Git Repository Detection
**Goal**: Verify we're in a git repository and get basic info

**Tasks**:
- Check if current directory is in a git repository
- Get current branch name
- Validate we're not on a detached HEAD
- Add error handling for non-git directories

### Step 3: Error State Management
**Goal**: Implement the error file system for blocking on previous failures

**Tasks**:
- Check for existing `AUTO-BLACK-FORMATTING-ERROR` file on startup
- Create error file writing function
- Add error file cleanup instruction messages
- Implement graceful abort when error file exists

### Step 4: Git Stashing
**Goal**: Safely save and restore working directory changes

**Tasks**:
- Implement `git stash` with proper error checking
- Create stash pop function with conflict handling
- Add stash verification (check if stash was created)
- Implement rollback function that restores stash on error

### Step 5: Merge Base Detection
**Goal**: Find the base commit for creating formatting branch

**Tasks**:
- Implement `git merge-base HEAD main` command
- Handle cases where main branch doesn't exist (try master, origin/main, etc.)
- Add error handling for repos without main branch
- Validate merge-base commit exists

### Step 6: File Existence Validation
**Goal**: Check which files exist at the merge-base commit

**Tasks**:
- Check file existence at merge-base using `git show`
- Separate files into "existing at base" vs "new files"
- Add file path validation (must be Python files)
- Create file categorization logic

### Step 7: Branch Creation and Management
**Goal**: Create and manage the formatting branch

**Tasks**:
- Generate formatting branch name from current branch
- Create branch from merge-base commit
- Check for existing formatting branch and reuse if found
- Add branch cleanup on errors

### Step 8: Black Formatting Integration
**Goal**: Apply black formatting to files

**Tasks**:
- Run black on specified files with error capture
- Validate black is installed and accessible
- Handle black formatting errors gracefully
- Check if formatting actually changed files

### Step 9: Commit Formatting Changes
**Goal**: Commit the formatted changes to formatting branch

**Tasks**:
- Add formatted files to git index
- Create commit with standardized message
- Handle case where no changes were made
- Verify commit was created successfully

### Step 10: Branch Switching and Merging
**Goal**: Return to original branch and merge formatting changes

**Tasks**:
- Switch back to original branch
- Merge formatting branch with conflict detection
- Handle merge conflicts with proper cleanup
- Verify merge was successful

### Step 11: Background GitHub Operations Setup
**Goal**: Prepare for background push and PR creation

**Tasks**:
- Create background process function structure
- Implement process forking mechanism
- Add signal handling for cleanup
- Create background error logging to error file

### Step 12: GitHub Push Implementation
**Goal**: Push formatting branch to remote in background

**Tasks**:
- Implement remote push with authentication
- Add retry logic for network failures
- Handle push conflicts (force push with lease)
- Log push success/failure to background log

### Step 13: GitHub PR Creation
**Goal**: Create PR for formatting changes

**Tasks**:
- Use GitHub CLI to create PR
- Handle existing PR detection (update instead of create)
- Set appropriate PR title and description
- Handle PR creation failures gracefully

### Step 14: Final Integration and Polish
**Goal**: Wire everything together and add final touches

**Tasks**:
- Integrate all components into main workflow
- Add comprehensive error handling and rollback
- Implement quiet mode for IDE integration
- Add performance timing and optimization

## Implementation Guidelines

### Development Principles
1. **Incremental Safety**: Each chunk must be fully functional and testable
2. **Error-First Design**: Implement error handling alongside each feature
3. **State Integrity**: Never leave git repository in inconsistent state
4. **Performance Awareness**: Keep local operations under 1 second
5. **User Experience**: Provide clear feedback for all operations

### Quality Standards
- All git operations must be reversible
- Error messages must be actionable
- No orphaned branches or uncommitted changes
- Graceful degradation for network failures
- Comprehensive logging for debugging

### Testing Strategy
- Unit tests for each git operation
- Integration tests for complete workflows
- Error scenario testing for each failure point
- Performance testing for large file sets
- IDE integration testing

## Risk Mitigation

### High-Risk Areas
1. **Git State Corruption**: Multiple safeguards and verification steps
2. **Merge Conflicts**: Comprehensive conflict detection and recovery
3. **Background Process Failures**: Robust error logging and user notification
4. **Network Failures**: Graceful degradation and retry mechanisms
5. **File System Permissions**: Proper permission checking and error handling

### Contingency Plans
- Automated rollback for any git operation failure
- Manual recovery procedures documented for each error type
- Background process monitoring and cleanup
- User guidance for manual conflict resolution
- Alternative workflows for network-constrained environments

## Implementation Prompts

Each step below is designed to be implemented incrementally, building on the previous steps. Execute these prompts in order.

### Prompt 1: Basic Shell Script Foundation

```
Create a shell script called 'brack' that serves as the foundation for an auto-formatting tool. The script should:

1. Start with proper shebang (#!/bin/bash)
2. Accept one or more file paths as command-line arguments
3. Display usage/help when called with -h, --help, or no arguments
4. Validate that all provided arguments are file paths
5. Add basic error handling with proper exit codes
6. Include a main() function that processes the arguments

Requirements:
- Use 'set -euo pipefail' for strict error handling
- Print errors to stderr
- Exit with code 1 on errors, 0 on success
- Make the script executable (chmod +x brack)
- Add basic logging function that can be used throughout

The script should validate arguments but not yet perform any git or formatting operations. Focus on creating a solid foundation with proper argument parsing and error handling.
```

### Prompt 2: Git Repository Detection

```
Extend the 'brack' script to detect and validate git repository information. Add these functions:

1. check_git_repo() - Verify we're in a git repository
2. get_current_branch() - Get the current branch name
3. validate_git_state() - Ensure we're not on detached HEAD

Requirements:
- Use 'git rev-parse --git-dir' to check for git repository
- Use 'git branch --show-current' to get current branch
- Handle cases where commands fail gracefully
- Add informative error messages for non-git directories
- Exit early if git validation fails
- Store branch name in a global variable for later use

Integration:
- Call these functions from main() before processing files
- Ensure the script exits cleanly if not in a proper git repository
- Add debug output showing the detected branch name
```

### Prompt 3: Error State Management

```
Add error state management to the 'brack' script to handle previous operation failures. Implement:

1. check_error_file() - Check for AUTO-BLACK-FORMATTING-ERROR file
2. create_error_file() - Write error details to the error file
3. show_error_instructions() - Display cleanup instructions to user

Requirements:
- Error file should be created in git repository root
- Include timestamp, error message, command context, and branch info
- If error file exists on startup, show instructions and exit
- Error file content should help user understand what went wrong
- Add function to find git repository root using 'git rev-parse --show-toplevel'

Error file format:
```
TIMESTAMP: [ISO timestamp]
BRANCH: [branch name]
COMMAND: [command that failed]
ERROR: [error message]
DIRECTORY: [working directory]

To resolve: Review the error above, fix any issues, then delete this file to continue.
```

Integration:
- Call check_error_file() early in main()
- Use create_error_file() in error handling paths (placeholder for now)
- Test by manually creating an error file and running the script
```

### Prompt 4: Git Stashing Implementation

```
Add git stashing functionality to safely preserve working directory changes. Implement:

1. git_stash_save() - Create a stash if there are changes
2. git_stash_pop() - Restore the stash with conflict handling
3. has_working_changes() - Check if working directory has changes
4. rollback_stash() - Emergency stash restoration

Requirements:
- Use 'git status --porcelain' to detect changes
- Only create stash if there are actually changes to save
- Track whether a stash was created (global variable)
- Handle stash pop conflicts gracefully
- Add error handling for all git stash operations
- Include 'git stash list' verification

Stash workflow:
- Save stash at start of operations
- Set flag indicating stash was created
- In error handlers, call rollback_stash() if stash exists
- In success path, call git_stash_pop() to restore changes

Integration:
- Add stash save call after git validation in main()
- Create placeholder error handling that calls rollback_stash()
- Test with both clean and dirty working directories
```

### Prompt 5: Merge Base Detection

```
Implement merge base detection to find the base commit for the formatting branch. Add:

1. find_main_branch() - Detect main/master branch name
2. get_merge_base() - Find merge base between current branch and main
3. validate_merge_base() - Ensure merge base commit exists

Requirements:
- Try multiple main branch candidates: main, master, origin/main, origin/master
- Use 'git merge-base HEAD <main-branch>' to find base commit
- Validate merge base using 'git cat-file -e <commit>'
- Handle repositories without a main branch
- Store merge base commit hash in global variable

Branch detection logic:
1. Check if 'main' branch exists locally
2. Check if 'master' branch exists locally  
3. Check if 'origin/main' exists
4. Check if 'origin/master' exists
5. Error if none found

Integration:
- Call after stash save in main workflow
- Use the merge base for creating formatting branch later
- Add error handling that calls rollback_stash() on failure
- Test in repositories with different main branch names
```

### Prompt 6: File Existence Validation

```
Add file validation logic to categorize files as existing vs new. Implement:

1. validate_python_files() - Ensure all files are Python files
2. check_file_at_commit() - Test if file exists at specific commit
3. categorize_files() - Separate existing files from new files

Requirements:
- Validate file extensions (.py files only)
- Use 'git show <commit>:<filepath>' to check file existence at merge base
- Create two arrays: EXISTING_FILES and NEW_FILES
- Handle file paths with spaces properly
- Provide informative messages about file categorization

File categorization logic:
- For each input file, check if it exists at merge base commit
- Files that exist at merge base go to EXISTING_FILES
- Files that don't exist (new files) go to NEW_FILES
- Validate all files are .py files before categorization

Integration:
- Call after merge base detection
- Use file arrays in subsequent formatting operations
- Add debug output showing file categorization
- Handle case where no files exist at merge base
```

### Prompt 7: Branch Creation and Management

```
Implement formatting branch creation and management. Add:

1. generate_branch_name() - Create formatting branch name from current branch
2. create_formatting_branch() - Create or checkout existing formatting branch
3. cleanup_formatting_branch() - Delete formatting branch on errors

Requirements:
- Branch name format: {current-branch}-auto-black-formatting
- Create branch from merge base commit if it doesn't exist
- If branch exists, checkout and reset to merge base
- Use 'git checkout -b' for new branches
- Use 'git checkout' + 'git reset --hard' for existing branches
- Store formatting branch name in global variable

Branch management:
- Check if formatting branch already exists
- If exists: checkout and reset to merge base (clean slate)
- If not exists: create from merge base
- Add error handling with proper cleanup
- Ensure we can return to original branch

Integration:
- Call after file categorization
- Only create branch if there are EXISTING_FILES to format
- Add cleanup call to error handlers
- Test branch creation and reuse scenarios
```

### Prompt 8: Black Formatting Integration

```
Add black formatting functionality with proper error handling. Implement:

1. check_black_available() - Verify black is installed and accessible
2. format_files_with_black() - Apply black formatting to file list
3. check_formatting_changes() - Detect if formatting changed files

Requirements:
- Use 'command -v black' to check if black is available
- Run black with proper error capture: 'black --check --diff' first
- Apply formatting with 'black <files>'
- Capture black stderr and stdout separately
- Detect if any files were actually modified
- Handle black syntax errors gracefully

Black workflow:
1. Verify black is available
2. For EXISTING_FILES (while on formatting branch):
   - Run black formatting
   - Check if files were modified
3. For NEW_FILES (will be handled differently later):
   - Skip for now, handle in current branch

Integration:
- Call after creating formatting branch
- Only format EXISTING_FILES when on formatting branch
- Add black errors to error file creation
- Return to original branch and call rollback on black failures
```

### Prompt 9: Commit Formatting Changes

```
Implement committing of formatting changes on the formatting branch. Add:

1. stage_formatted_files() - Add files to git index
2. create_formatting_commit() - Commit with standard message
3. verify_commit_created() - Ensure commit was successful

Requirements:
- Use 'git add' to stage only the formatted files
- Commit message: "black" (as specified in requirements)
- Check if any changes were actually staged before committing
- Use 'git diff --cached --quiet' to check for staged changes
- Handle case where formatting made no changes
- Store commit hash if created

Commit workflow:
1. Stage the EXISTING_FILES that were formatted
2. Check if there are staged changes
3. If changes exist, create commit
4. If no changes, skip commit but continue
5. Verify commit was created successfully

Integration:
- Call after black formatting on formatting branch
- Handle "no changes" case gracefully (not an error)
- Add commit verification to ensure git operation succeeded
- Include commit info in error messages if later operations fail
```

### Prompt 10: Branch Switching and Merging

```
Implement the workflow to return to original branch and merge formatting changes. Add:

1. return_to_original_branch() - Switch back from formatting branch
2. merge_formatting_branch() - Merge formatting changes into current branch
3. handle_merge_conflicts() - Detect and handle merge conflicts

Requirements:
- Use 'git checkout' to return to original branch
- Use 'git merge --no-ff' to merge formatting branch
- Capture merge output and detect conflicts
- On merge conflicts: abort merge and call error cleanup
- Verify merge completed successfully
- Clean up formatting branch after successful merge

Merge workflow:
1. Switch back to original branch
2. Attempt to merge formatting branch
3. If merge succeeds: continue to stash pop
4. If merge fails: abort merge, cleanup, and error exit
5. Delete formatting branch after successful merge

Integration:
- Call after commit creation (or skip if no commit)
- Handle merge conflicts by aborting and cleaning up
- Ensure we're on original branch before stash pop
- Add comprehensive error handling with rollback
```

### Prompt 11: Background GitHub Operations Setup

```
Set up the foundation for background GitHub operations. Implement:

1. setup_background_operations() - Prepare for background tasks
2. fork_github_operations() - Fork process for GitHub tasks
3. log_background_error() - Write background errors to error file

Requirements:
- Create background operation functions (push/PR creation)
- Use shell background process (&) for GitHub operations
- Implement proper signal handling for cleanup
- Create background error logging that writes to error file
- Add process ID tracking for cleanup

Background process structure:
- Create function github_operations() that handles push and PR
- Fork this function to background after successful merge
- Parent process continues and completes normally
- Background process logs errors to error file if operations fail
- Add trap handlers for signal cleanup

Implementation notes:
- Don't implement actual push/PR yet - just the background framework
- Focus on process management and error logging
- Test background process creation and error file writing
- Ensure parent process doesn't wait for background completion
```

### Prompt 12: GitHub Push Implementation

```
Implement GitHub push functionality for the background process. Add:

1. push_formatting_branch() - Push formatting branch to remote
2. handle_push_authentication() - Deal with auth requirements
3. retry_push() - Implement push retry logic

Requirements:
- Use 'git push origin <formatting-branch>' for initial push
- Use 'git push --force-with-lease' for subsequent pushes
- Detect authentication failures and provide helpful messages
- Implement 3 retry attempts with exponential backoff
- Log all push attempts and results
- Handle network timeouts gracefully

Push workflow:
1. Attempt initial push to origin
2. If push fails due to conflicts, use force-with-lease
3. If authentication fails, log helpful error message
4. Retry up to 3 times with 1s, 2s, 4s delays
5. Log final success or failure to error file

Integration:
- Call from github_operations() background function
- Run only after successful local merge
- Don't block main process - handle all errors in background
- Write detailed error info to error file on failures
```

### Prompt 13: GitHub PR Creation

```
Implement GitHub PR creation using GitHub CLI. Add:

1. create_or_update_pr() - Create new PR or update existing
2. check_existing_pr() - Look for existing PR for formatting branch
3. format_pr_description() - Generate appropriate PR title/description

Requirements:
- Use 'gh pr create' for new PRs
- Use 'gh pr edit' for updating existing PRs
- Check for existing PRs with 'gh pr list'
- Handle cases where gh CLI is not authenticated
- Use descriptive PR title: "Auto-format with black: {original-branch}"
- Include file list in PR description

PR workflow:
1. Check if PR already exists for formatting branch
2. If exists: update PR with new changes
3. If not exists: create new PR
4. Handle gh CLI authentication errors
5. Log PR URL or creation errors

PR description template:
```
Automated black formatting for files:
- {file1}
- {file2}
- ...

Generated by brack tool.
```

Integration:
- Call after successful push in background process
- Handle both PR creation and update scenarios
- Log PR URL to stdout (background process)
- Log errors to error file with helpful auth guidance
```

### Prompt 14: Final Integration and Polish

```
Complete the integration of all components and add final polish. Implement:

1. integrate_full_workflow() - Wire all components together in main()
2. add_performance_timing() - Add timing for performance requirements
3. implement_quiet_mode() - Add silent operation for IDE integration
4. comprehensive_error_handling() - Ensure all error paths are covered

Requirements:
- Complete main() function with full workflow
- Add timing to meet <1 second local operation requirement
- Add --quiet flag for silent operation (IDE integration)
- Ensure all error paths call appropriate cleanup functions
- Add final validation of all operations
- Handle NEW_FILES formatting in current branch

Full workflow integration:
1. Parse arguments and validate
2. Check error file and git state
3. Stash working changes
4. Find merge base and categorize files
5. Create formatting branch and format EXISTING_FILES
6. Commit changes and merge back
7. Format NEW_FILES in current branch (if any)
8. Restore stash
9. Start background GitHub operations
10. Exit successfully

Final touches:
- Add comprehensive testing of all error scenarios
- Optimize git operations for speed
- Add debug mode with verbose output
- Ensure script handles edge cases gracefully
- Validate performance meets requirements (<1s local ops)
```