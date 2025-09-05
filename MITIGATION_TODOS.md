# BRACK ISSUE MITIGATION TODO LIST
# Priority-ordered tasks to fix data loss risks

## CRITICAL PRIORITY - Immediate Action Required

### STASH SAFETY IMPROVEMENTS

#### TODO-STASH-001: Implement Robust Stash Validation
- [ ] Add `validate_stash_exists()` function to verify stash before attempting restore
- [ ] Implement stash content verification (file count, checksum validation)
- [ ] Add stash backup mechanism before any destructive operations
- [ ] **Location**: Modify `restore_working_directory()` at line 429
- [ ] **Risk**: Without this, stashed work can be permanently lost

#### TODO-STASH-002: Improve Stash Recovery Error Handling
- [ ] Replace silent failures in `cleanup_stash_on_error()` with explicit error reporting
- [ ] Add fallback mechanisms when primary stash recovery fails
- [ ] Implement stash history logging to track what was stashed when
- [ ] **Location**: Modify `cleanup_stash_on_error()` at line 472
- [ ] **Risk**: Current silent failures leave users unaware of data loss

#### TODO-STASH-003: Add Stash Safety Checks Before Branch Operations
- [ ] Verify working directory is clean before any branch switching
- [ ] Add confirmation prompt when stashing untracked files
- [ ] Implement dry-run mode for stash operations
- [ ] **Location**: Add checks before `git checkout` operations at lines 867, 889, 911
- [ ] **Risk**: Branch switching can silently destroy untracked files

### UNTRACKED FILE PROTECTION

#### TODO-UNTRACKED-001: Remove Dangerous -u Flag from Stash Operations
- [ ] Separate tracked and untracked file handling completely
- [ ] Replace `git stash push -u` with tracked-only stashing
- [ ] Add explicit untracked file backup mechanism using tar/zip
- [ ] **Location**: Modify `save_working_directory()` at line 403
- [ ] **Risk**: CRITICAL - -u flag is primary cause of untracked file loss

#### TODO-UNTRACKED-002: Implement Untracked File Safety Scanner
- [ ] Add `scan_untracked_files()` function to inventory untracked files before operations
- [ ] Create manifest of untracked files with checksums
- [ ] Validate untracked files are unchanged after operations
- [ ] **Location**: Add new function, call before any git operations
- [ ] **Risk**: Without inventory, impossible to detect untracked file loss

#### TODO-UNTRACKED-003: Add Untracked File Categorization 
- [ ] Extend file categorization to include untracked Python files
- [ ] Add special handling for untracked files that would be formatted
- [ ] Implement user confirmation for formatting untracked files
- [ ] **Location**: Modify `categorize_files()` at line 765
- [ ] **Risk**: Untracked Python files may not be formatted correctly

#### TODO-UNTRACKED-004: Implement Safe Branch Switching
- [ ] Add pre-flight check for untracked files before branch switching
- [ ] Warn user about potential untracked file conflicts
- [ ] Add option to backup untracked files before branch operations
- [ ] **Location**: Modify all `git checkout` operations
- [ ] **Risk**: Branch switching can silently delete conflicting untracked files

## HIGH PRIORITY - Address Within Sprint

### RACE CONDITION PREVENTION

#### TODO-RACE-001: Implement File Locking for Concurrent Execution
- [ ] Add exclusive lock file creation at tool startup
- [ ] Implement lock timeout and stale lock detection
- [ ] Add graceful handling when lock is already held
- [ ] **Location**: Add to `main()` function at line 2436
- [ ] **Risk**: Multiple invocations can corrupt git state

#### TODO-RACE-002: Add Background Process Tracking
- [ ] Create persistent background process registry
- [ ] Implement orphaned process detection and cleanup
- [ ] Add process health monitoring for background operations
- [ ] **Location**: Modify background process functions starting line 1161
- [ ] **Risk**: Orphaned processes interfere with subsequent runs

#### TODO-RACE-003: Implement Atomic Error State Management
- [ ] Use atomic file operations for error state file updates
- [ ] Add process ID tracking to error state file
- [ ] Implement error state file locking
- [ ] **Location**: Modify error state functions at lines 177-257
- [ ] **Risk**: Corrupted error state files block all operations

### MERGE CONFLICT SAFETY

#### TODO-MERGE-001: Replace Silent Conflict Resolution
- [ ] Remove automatic `git checkout --ours .` behavior
- [ ] Add user prompt for conflict resolution strategy
- [ ] Implement conflict diff display before resolution
- [ ] **Location**: Modify `handle_merge_conflicts()` at line 1050
- [ ] **Risk**: Important changes silently discarded during conflicts

#### TODO-MERGE-002: Add Conflict Resolution Logging
- [ ] Log all files affected by conflict resolution
- [ ] Create before/after diffs of conflict resolution
- [ ] Add recovery instructions for undoing conflict resolution
- [ ] **Location**: Add logging to conflict resolution functions
- [ ] **Risk**: Users unaware of what was lost during conflict resolution

### ERROR RECOVERY IMPROVEMENTS

#### TODO-RECOVERY-001: Implement Bulletproof Emergency Cleanup
- [ ] Make each cleanup step independent and reversible
- [ ] Add comprehensive logging of cleanup operations
- [ ] Implement cleanup verification and rollback mechanisms
- [ ] **Location**: Rewrite `emergency_cleanup()` at line 530
- [ ] **Risk**: Failed cleanup leaves repository in broken state

#### TODO-RECOVERY-002: Add Pre-Operation State Backup
- [ ] Create complete repository state snapshot before operations
- [ ] Include working directory, index, and stash state
- [ ] Add one-command state restoration mechanism
- [ ] **Location**: Add to beginning of `main_workflow()` at line 2195
- [ ] **Risk**: No way to recover from catastrophic failures

## MEDIUM PRIORITY - Address Next Sprint

### FORCE PUSH SAFETY

#### TODO-PUSH-001: Add User Confirmation for Force Push
- [ ] Require explicit user consent for --force-with-lease operations
- [ ] Add dry-run mode to show what would be pushed
- [ ] Implement push conflict detection before attempting force push
- [ ] **Location**: Modify `push_branch_with_retry()` at line 1448

#### TODO-PUSH-002: Improve Background Operation Transparency
- [ ] Add real-time status display for background operations
- [ ] Implement background operation cancellation
- [ ] Add comprehensive logging of background git operations
- [ ] **Location**: Modify background process framework starting line 1174

### USER EXPERIENCE IMPROVEMENTS

#### TODO-UX-001: Add Comprehensive Warnings
- [ ] Add prominent warning about untracked file risks
- [ ] Implement --check-only mode to show potential risks before execution  
- [ ] Add confirmation prompts for high-risk operations
- [ ] **Location**: Add to help text and before dangerous operations

#### TODO-UX-002: Implement Detailed Operation Logging
- [ ] Add comprehensive audit log of all git operations
- [ ] Include timing, results, and error information
- [ ] Implement log rotation and cleanup
- [ ] **Location**: Add logging throughout all git operations

## TESTING REQUIREMENTS

### TODO-TEST-001: Create Data Loss Regression Tests
- [ ] Test stash failure scenarios with untracked files
- [ ] Test concurrent execution race conditions
- [ ] Test emergency cleanup under various failure conditions
- [ ] **Location**: Add to existing test suite

### TODO-TEST-002: Create Untracked File Test Suite
- [ ] Test branch switching with conflicting untracked files
- [ ] Test stash/restore with various untracked file types
- [ ] Test directory structure changes with untracked files
- [ ] **Location**: Create new test file for untracked scenarios

---

## IMPLEMENTATION PRIORITY ORDER

1. **TODO-UNTRACKED-001**: Remove -u flag (CRITICAL - prevents most data loss)
2. **TODO-RACE-001**: File locking (HIGH - prevents concurrent corruption)
3. **TODO-STASH-001**: Stash validation (CRITICAL - detects stash failures)
4. **TODO-RECOVERY-001**: Bulletproof cleanup (HIGH - prevents broken states)
5. **TODO-UNTRACKED-002**: Untracked file scanner (HIGH - detects untracked issues)

*Each TODO should be implemented as a separate, testable change with full regression testing.*