"""Orchestrates the full brack workflow.

See ``spec.md`` for behavioural contract. The key invariants:
  * The working tree is always returned to the original branch.
  * If the working tree was dirty on entry, its changes are restored (stash pop).
  * The formatting branch is reused across runs of the same feature branch.
  * Merge conflicts are auto-resolved by keeping the feature branch's version
    (``-X ours``) since black is re-applied afterwards.
  * GitHub push / PR ops are fire-and-forget unless ``no_background`` is set.
  * Any failure leaves an ``AUTO-BLACK-FORMATTING-ERROR`` file for investigation.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import black_runner, github_ops
from .config import Config
from .error_state import (
    append_background_error,
    clear_error_state,
    error_state_present,
    write_error_state,
)
from .errors import (
    BlackFailure,
    BrackError,
    ErrorStatePresentError,
    GitFailure,
    InvalidArgsError,
    MergeConflictError,
    NotAGitRepoError,
)
from .git_ops import GitRunner
from .logging import Logger


@dataclass
class RunResult:
    """Outcome of a single :func:`run` invocation."""

    formatted_existing: list[str] = field(default_factory=list)
    formatted_new: list[str] = field(default_factory=list)
    skipped: bool = False  # True when nothing to format
    formatting_branch: str | None = None
    main_branch: str | None = None
    duration_ms: int = 0
    background_jobs: list[github_ops.BackgroundJob] = field(default_factory=list)

    @property
    def formatted(self) -> list[str]:
        return [*self.formatted_existing, *self.formatted_new]


# ---------- helpers ---------------------------------------------------------


def _resolve_file_args(config: Config, repo_root: Path) -> list[str]:
    """Normalise user-supplied file args to repo-relative POSIX paths.

    Raises :class:`InvalidArgsError` for non-``.py`` paths and
    :class:`BrackError` for paths outside the repo.
    """
    rel: list[str] = []
    for f in config.files:
        if not f.endswith(".py"):
            raise InvalidArgsError(f"'{f}' is not a Python file (must have .py extension)")
        abs_path = Path(f) if Path(f).is_absolute() else (config.cwd / f)
        abs_path = abs_path.resolve()
        if not abs_path.exists():
            raise BrackError(f"File '{f}' does not exist", context="file validation")
        try:
            rel_path = abs_path.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise BrackError(
                f"File '{f}' is outside the git repository '{repo_root}'",
                context="file validation",
            ) from exc
        rel.append(rel_path.as_posix())
    return rel


def _discover_py_files(repo_root: Path) -> list[str]:
    paths = []
    for p in repo_root.rglob("*.py"):
        if ".git" in p.parts:
            continue
        paths.append(p.relative_to(repo_root).as_posix())
    return sorted(paths)


def _categorize(
    git: GitRunner, merge_base: str, files: Iterable[str]
) -> tuple[list[str], list[str]]:
    existing, new = [], []
    for f in files:
        if git.file_exists_at(merge_base, f):
            existing.append(f)
        else:
            new.append(f)
    return existing, new


def _commit_message(prefix: str, changed: list[str], *, new_files: bool = False) -> str:
    suffix = " new file" if new_files else ""
    if len(changed) == 1:
        return f"{prefix} to{suffix} {changed[0]}"
    label = f"{len(changed)} new files" if new_files else f"{len(changed)} files"
    return f"{prefix} to {label}"


# ---------- main entrypoint -----------------------------------------------


def run(config: Config, *, logger: Logger | None = None) -> RunResult:
    logger = logger or Logger(quiet=config.quiet, verbose=config.verbose)

    # 1. Resolve repo root from either a supplied file or the cwd.
    anchor = Path(config.files[0]) if config.files else config.cwd
    if not anchor.is_absolute():
        anchor = config.cwd / anchor
    try:
        repo_root = GitRunner.find_repo_root(anchor)
    except NotAGitRepoError:
        raise

    # 2. Handle --cleanup before anything else.
    if config.cleanup:
        if clear_error_state(repo_root):
            logger.success("Error state cleaned up successfully")
        else:
            logger.info("No error state file found")
        return RunResult(skipped=True)

    # 3. Refuse to run while an error state file exists.
    if error_state_present(repo_root):
        raise ErrorStatePresentError(
            f"Previous error state detected at {repo_root}. "
            "Run 'brack --cleanup' after resolving the issue."
        )

    # 4. Validate git environment.
    git = GitRunner(repo_root)
    current_branch = git.current_branch()
    logger.debug(f"repo={repo_root} branch={current_branch}")

    main_branch = config.main_branch or git.detect_main_branch()
    merge_base = git.merge_base("HEAD", main_branch)

    # 5. Resolve the files to format.
    if config.files:
        files = _resolve_file_args(config, repo_root)
    else:
        files = _discover_py_files(repo_root)

    if not files:
        logger.info("No Python files found to format")
        return RunResult(skipped=True, main_branch=main_branch)

    existing, new = _categorize(git, merge_base, files)
    formatting_branch = f"{current_branch}{config.formatting_branch_suffix}"

    # 6. Dry run: report what would happen and exit.
    if config.dry_run:
        logger.info("DRY RUN: No git changes will be made")
        logger.info(f"DRY RUN: Would format {len(existing)} existing file(s) in {formatting_branch}")
        logger.info(f"DRY RUN: Would format {len(new)} new file(s) in {current_branch}")
        return RunResult(
            formatted_existing=existing,
            formatted_new=new,
            formatting_branch=formatting_branch,
            main_branch=main_branch,
        )

    # 7. Check black availability.
    black_path = black_runner.resolve_black(config.black_path)

    start = time.monotonic()
    result = RunResult(formatting_branch=formatting_branch, main_branch=main_branch)

    try:
        _do_workflow(
            config=config,
            logger=logger,
            git=git,
            repo_root=repo_root,
            black_path=black_path,
            current_branch=current_branch,
            main_branch=main_branch,
            merge_base=merge_base,
            existing=existing,
            new=new,
            formatting_branch=formatting_branch,
            result=result,
        )
    except BrackError as exc:
        _emergency_rollback(git, current_branch, logger)
        write_error_state(repo_root, exc.message, exc.context or "brack workflow")
        raise
    except Exception as exc:
        _emergency_rollback(git, current_branch, logger)
        write_error_state(repo_root, str(exc), "unexpected error")
        raise

    result.duration_ms = int((time.monotonic() - start) * 1000)

    if config.quiet:
        count = len(result.formatted)
        if count:
            logger.out(f"brack: formatted {count} file(s) in {result.duration_ms}ms")
        if result.duration_ms > 2000:
            print(f"brack: warning: slow performance {result.duration_ms}ms", flush=True)
    else:
        logger.success(f"Workflow completed successfully in {result.duration_ms}ms")

    return result


# ---------- inner workflow --------------------------------------------------


def _do_workflow(
    *,
    config: Config,
    logger: Logger,
    git: GitRunner,
    repo_root: Path,
    black_path: str,
    current_branch: str,
    main_branch: str,
    merge_base: str,
    existing: list[str],
    new: list[str],
    formatting_branch: str,
    result: RunResult,
) -> None:
    # 1. Stash dirty working tree so branch switch is safe.
    stash_msg = f"brack-auto-stash-{int(time.time())}"
    stashed = git.stash_push(stash_msg)
    if stashed:
        logger.info("Stashed uncommitted changes")

    # 2. Enter or create the formatting branch.
    if existing:
        if git.branch_exists(formatting_branch):
            logger.info(f"Reusing formatting branch {formatting_branch}")
            git.checkout(formatting_branch)
        else:
            logger.info(f"Creating formatting branch {formatting_branch}")
            git.checkout_new(formatting_branch, merge_base)

        # 3. Format existing files.
        fmt_result = black_runner.run_black(
            black_path, existing, extra_args=config.black_args, cwd=repo_root
        )
        if fmt_result.changed:
            git.add(*fmt_result.changed)
            if git.has_staged_changes():
                git.commit(_commit_message(config.commit_message_prefix, fmt_result.changed))
                result.formatted_existing = fmt_result.changed

        # 4. Fire off background GitHub ops (before returning to original branch).
        if result.formatted_existing:
            _schedule_github_ops(
                config=config,
                logger=logger,
                repo_root=repo_root,
                formatting_branch=formatting_branch,
                main_branch=main_branch,
                files=result.formatted_existing,
                result=result,
            )

        # 5. Return to original branch and merge.
        git.checkout(current_branch)
        try:
            git.merge(
                formatting_branch,
                message=f"Merge formatting changes from {formatting_branch}",
            )
        except GitFailure as exc:
            if git.in_merge_state():
                git.merge_abort()
            raise MergeConflictError(
                "Merge of formatting branch failed",
                context=exc.context,
            ) from exc

    # 6. Format new files in the feature branch itself.
    if new:
        fmt_new = black_runner.run_black(
            black_path, new, extra_args=config.black_args, cwd=repo_root
        )
        if fmt_new.changed:
            git.add(*fmt_new.changed)
            if git.has_staged_changes():
                git.commit(
                    _commit_message(
                        config.commit_message_prefix, fmt_new.changed, new_files=True
                    )
                )
                result.formatted_new = fmt_new.changed

    # 7. Restore the stash.
    if stashed:
        try:
            git.stash_pop()
            logger.info("Restored stashed changes")
        except GitFailure as exc:
            # Leave the user in the conflict state to resolve manually; this
            # is the spec's prescribed behaviour.
            logger.error(
                "Stash pop failed; resolve conflicts manually (stash list has your changes)"
            )
            raise BrackError("stash pop failed", context=exc.context) from exc

        # Re-run black on restored local changes to new files — the spec calls
        # for this double-format so restored edits match the formatted state.
        if new:
            black_runner.run_black(
                black_path, new, extra_args=config.black_args, cwd=repo_root
            )

    if config.no_background:
        for job in result.background_jobs:
            job.join()


def _schedule_github_ops(
    *,
    config: Config,
    logger: Logger,
    repo_root: Path,
    formatting_branch: str,
    main_branch: str,
    files: list[str],
    result: RunResult,
) -> None:
    if config.no_push and config.no_pr:
        return

    def push_and_pr() -> None:
        try:
            if not config.no_push:
                outcome = github_ops.push_with_retry(formatting_branch, cwd=repo_root)
                if not outcome.success:
                    append_background_error(
                        repo_root, "github_push", outcome.returncode, f"git push {formatting_branch}"
                    )
                    return
            if config.no_pr:
                return
            if not github_ops.gh_authenticated(cwd=repo_root):
                append_background_error(repo_root, "github_pr", 2, "gh auth status")
                return
            base = main_branch.replace("origin/", "")
            title = github_ops.render_pr_title(formatting_branch)
            body = github_ops.render_pr_body(formatting_branch, base, files)
            existing_url = github_ops.find_existing_pr(formatting_branch, base, cwd=repo_root)
            if existing_url:
                r = github_ops.update_pr(existing_url, title=title, body=body, cwd=repo_root)
            else:
                r = github_ops.create_pr(formatting_branch, base, title=title, body=body, cwd=repo_root)
            if r.returncode != 0:
                append_background_error(
                    repo_root,
                    "github_pr",
                    r.returncode,
                    "gh pr edit" if existing_url else "gh pr create",
                )
        except Exception as exc:
            append_background_error(repo_root, "github", 1, repr(exc))

    if config.no_background:
        push_and_pr()
    else:
        result.background_jobs.append(github_ops.run_in_background(push_and_pr))


def _emergency_rollback(git: GitRunner, original_branch: str, logger: Logger) -> None:
    """Best-effort cleanup when the workflow aborts."""
    try:
        if git.in_merge_state():
            git.merge_abort()
        current = None
        try:
            current = git.current_branch()
        except GitFailure:
            pass
        if current and current != original_branch:
            try:
                git.checkout(original_branch)
            except GitFailure:
                logger.error(f"Manual recovery: git checkout {original_branch}")
    except Exception:
        logger.error("Emergency rollback partially failed; inspect repo state")
