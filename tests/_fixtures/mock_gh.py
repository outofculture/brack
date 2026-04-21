#!/usr/bin/env python3
"""Mock `gh` binary used by brack integration tests.

Every invocation is appended as a JSON line to the file at
``$BRACK_MOCK_GH_LOG`` (argv + cwd). Behaviour can be customised by writing a
JSON dict to ``$BRACK_MOCK_GH_CONFIG``::

    {
      "pr_create": {"exit": 0, "stdout": "https://github.com/x/y/pull/1"},
      "pr_list":   {"exit": 0, "stdout": ""},
      "pr_edit":   {"exit": 0, "stdout": ""},
      "auth":      {"exit": 0, "stdout": "Logged in"},
      "default":   {"exit": 0, "stdout": ""}
    }

If no config is given the tool behaves as a successful, freshly-authenticated
`gh` with no pre-existing PRs. That's the common case for happy-path tests.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "auth": {"exit": 0, "stdout": "Logged in to github.com as mock-user"},
    "pr_list": {"exit": 0, "stdout": ""},
    "pr_create": {"exit": 0, "stdout": "https://github.com/mock/repo/pull/1"},
    "pr_edit": {"exit": 0, "stdout": ""},
    "version": {"exit": 0, "stdout": "gh version 2.0.0 (mock)"},
    "default": {"exit": 0, "stdout": ""},
}


def _load_config() -> dict:
    path = os.environ.get("BRACK_MOCK_GH_CONFIG")
    if path and Path(path).exists():
        user = json.loads(Path(path).read_text())
        merged = {**DEFAULT_CONFIG, **user}
        return merged
    return DEFAULT_CONFIG


def _log_invocation(argv: list[str]) -> None:
    log_path = os.environ.get("BRACK_MOCK_GH_LOG")
    if not log_path:
        return
    record = {"argv": argv, "cwd": os.getcwd()}
    with open(log_path, "a") as fh:
        fh.write(json.dumps(record) + "\n")


def _classify(argv: list[str]) -> str:
    if "--version" in argv:
        return "version"
    if len(argv) < 2:
        return "default"
    if argv[1] == "auth":
        return "auth"
    if argv[1] == "pr" and len(argv) >= 3:
        sub = argv[2]
        if sub == "list":
            return "pr_list"
        if sub == "create":
            return "pr_create"
        if sub == "edit":
            return "pr_edit"
    return "default"


def main(argv: list[str]) -> int:
    _log_invocation(argv)
    config = _load_config()
    key = _classify(argv)
    entry = config.get(key, config["default"])
    stdout = entry.get("stdout", "")
    if stdout:
        sys.stdout.write(stdout)
        if not stdout.endswith("\n"):
            sys.stdout.write("\n")
    stderr = entry.get("stderr", "")
    if stderr:
        sys.stderr.write(stderr)
        if not stderr.endswith("\n"):
            sys.stderr.write("\n")
    return int(entry.get("exit", 0))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
