# KNOWN ISSUES - BRACK TOOL
# Critical Data Loss Risks and Mitigation Plan

## EXECUTIVE SUMMARY

The brack tool contains multiple critical issues that could result in permanent data loss, particularly involving git stash operations, untracked files, and race conditions. These issues pose significant risk to user work and should be addressed immediately.

## CRITICAL ISSUES

### 1. GIT STASH OPERATIONS - HIGH RISK (Lines 395-496)

**Problem**: Fragile stash recovery logic with multiple failure paths
- Uses `git stash push -u` but recovery may fail silently
- `cleanup_stash_on_error()` doesn't validate stash existence before attempting restore
- No verification that stashed content was successfully restored
- Emergency cleanup could fail leaving stashed work permanently inaccessible

**Data Loss Scenario**: User runs brack with uncommitted changes, tool crashes during execution, stashed work is never recovered.

**Files Affected**: `brack:395-496` (stashing functions)

### 2. UNTRACKED FILE VULNERABILITIES - CRITICAL RISK

**Problem**: Untracked files handled unsafely during branch operations
- `-u` flag in `git stash push -u` includes untracked files but recovery is not validated
- Branch switching can silently delete untracked files that conflict with target branch
- New Python files (untracked) may not be properly categorized for formatting
- Directory structure changes between branches can cause restoration failures

**Data Loss Scenarios**:
- New important module files lost during branch switching
- Configuration files overwritten by different branch versions  
- Build artifacts corrupted causing development environment breakage

**Files Affected**: `brack:403, 777-792, 867, 889, 911`

### 3. RACE CONDITIONS - HIGH RISK 

**Problem**: Multiple brack invocations can interfere with each other
- Single error state file `AUTO-BLACK-FORMATTING-ERROR` not protected by file locks
- Background processes not tracked across invocations
- Concurrent git operations can corrupt repository state
- No prevention of simultaneous stash/unstash operations

**Data Loss Scenario**: User runs brack in multiple terminals, git operations conflict, working directory left in inconsistent state.

**Files Affected**: `brack:177-257, 1161-1337`

### 4. DANGEROUS FORCE PUSH OPERATIONS - MEDIUM RISK (Lines 1470-1471)

**Problem**: Background force-push operations without user awareness
- Uses `--force-with-lease` which can still be destructive
- Network failures during push can leave repository inconsistent
- User may not realize background operations are modifying remote repository

**Files Affected**: `brack:1470-1471`

### 5. MERGE CONFLICT AUTO-RESOLUTION - MEDIUM RISK (Lines 1050-1091)

**Problem**: Automatic conflict resolution silently discards changes
- Always takes coding branch changes with `git checkout --ours .`
- May discard important formatting updates without user notification
- No logging of what was discarded during conflict resolution

**Files Affected**: `brack:1050-1091`

### 6. EMERGENCY CLEANUP FAILURE PATHS - HIGH RISK (Lines 530-574)

**Problem**: Complex cleanup sequence prone to cascading failures
- Multi-step cleanup could fail at any point leaving repository broken
- Signal handlers may not execute properly during system shutdown
- Failed cleanup could leave user stranded on wrong branch with lost stash

**Files Affected**: `brack:530-574, 577-583`

## SPECIFIC UNTRACKED FILE RISKS

### Critical Scenarios:

1. **New Python Module Loss**: Developer creates `new_feature.py`, runs brack, file gets stashed and lost during failed restoration
2. **Configuration File Corruption**: Untracked `.env` files overwritten by branch switching
3. **Build Environment Breakage**: Untracked build artifacts deleted/corrupted by branch operations
4. **Directory Structure Mismatch**: Files restored to non-existent directories after branch operations

### Code Locations:
- Line 403: `git stash push -u` includes untracked files unsafely
- Lines 777-792: File categorization doesn't account for untracked Python files
- Lines 867, 889, 911: Branch switching without untracked file safety checks

## AFFECTED USER WORKFLOWS

- **IDE Integration**: Risk increases with frequent automated runs
- **Active Development**: Highest risk when working on new features (untracked files)
- **Multiple Repository Windows**: Race conditions likely with concurrent usage
- **Network Instability**: Background operations more likely to fail and corrupt state

## SEVERITY CLASSIFICATION

- **CRITICAL**: Permanent data loss likely (stash failures, untracked file loss)
- **HIGH**: Data loss possible under common conditions (race conditions, cleanup failures)
- **MEDIUM**: Data loss possible under specific conditions (force push, conflict resolution)

## IMMEDIATE RECOMMENDATIONS

1. **Add prominent warning about untracked files to documentation**
2. **Implement file locking to prevent concurrent execution**
3. **Add robust stash validation and recovery mechanisms**
4. **Implement user confirmation for potentially destructive operations**
5. **Add comprehensive logging of all git operations**
6. **Create backup mechanisms for critical operations**

---
*Generated: $(date)*
*Reviewer: Security Analysis - Data Loss Risk Assessment*