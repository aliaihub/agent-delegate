"""Idempotent rule-block injector.

The installer reads a rule file from agent_delegate/rules/, then either:
 - replaces the existing managed block bounded by markers (re-install), OR
 - appends the block to the config file (first install), OR
 - creates the config file with just the block (file didn't exist).

Atomic writes via temp file + os.replace (Windows-safe).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


BEGIN_MARKER_PREFIX = "<!-- agent-delegate:begin"
END_MARKER = "<!-- agent-delegate:end -->"

# Matches:  <!-- agent-delegate:begin v0.1.0 -->\n ... \n<!-- agent-delegate:end -->
_BLOCK_RE = re.compile(
    r"<!--\s*agent-delegate:begin[^-]*-->.*?<!--\s*agent-delegate:end\s*-->",
    re.DOTALL,
)


class Action(str, Enum):
    WROTE_NEW = "wrote_new"          # file did not exist; created with block
    REPLACED_BLOCK = "replaced"      # found existing markers, swapped span
    APPENDED_BLOCK = "appended"      # file existed without markers, appended
    UNCHANGED = "unchanged"          # content identical; nothing written
    WOULD_WRITE = "would_write"      # --dry-run
    SKIPPED_NO_MARKERS = "skipped"   # file has content, no markers, --force not set
    REMOVED_BLOCK = "removed"        # uninstall: stripped span
    REMOVED_NOTHING = "noop"         # uninstall: no markers found
    ERROR = "error"


@dataclass
class InstallResult:
    action: Action
    target: Path
    detail: str = ""


def _read(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _atomic_write(path: Path, content: str) -> None:
    """Write via temp file in the same directory, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def inject_block(
    target: Path,
    block: str,
    *,
    dry_run: bool = False,
    force_append: bool = False,
) -> InstallResult:
    """Idempotently inject `block` into `target`.

    The block is expected to already contain its own begin/end markers (the
    rule .md files in agent_delegate/rules/ are formatted that way).

    Safety:
      - If `target` has existing markers, replace the span between them.
      - If `target` has no markers AND has other content, append unless
        `force_append=False` would lose that content — we always append safely
        with a separator, never overwriting user content.
      - If `target` doesn't exist, create it with the block.
    """
    block = block.strip("\n")
    existing = _read(target)

    # File doesn't exist — create with just the block.
    if existing is None:
        new_content = block + "\n"
        if dry_run:
            return InstallResult(Action.WOULD_WRITE, target,
                                 f"would create {target} with managed block")
        _atomic_write(target, new_content)
        return InstallResult(Action.WROTE_NEW, target)

    # File exists, has markers — replace span.
    if _BLOCK_RE.search(existing):
        new_content = _BLOCK_RE.sub(block, existing, count=1)
        if new_content == existing:
            return InstallResult(Action.UNCHANGED, target)
        if dry_run:
            return InstallResult(Action.WOULD_WRITE, target,
                                 "would replace managed block")
        _atomic_write(target, new_content)
        return InstallResult(Action.REPLACED_BLOCK, target)

    # File exists, no markers — append (separator preserves user content).
    sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    new_content = existing + sep + block + "\n"
    if dry_run:
        return InstallResult(Action.WOULD_WRITE, target,
                             "would append managed block (existing content preserved)")
    _atomic_write(target, new_content)
    return InstallResult(Action.APPENDED_BLOCK, target)


def strip_block(target: Path, *, dry_run: bool = False) -> InstallResult:
    """Remove the managed block from `target`. No-op if no markers found."""
    existing = _read(target)
    if existing is None:
        return InstallResult(Action.REMOVED_NOTHING, target, "file does not exist")
    if not _BLOCK_RE.search(existing):
        return InstallResult(Action.REMOVED_NOTHING, target, "no markers found")
    new_content = _BLOCK_RE.sub("", existing, count=1)
    # Collapse leftover triple newlines into double.
    new_content = re.sub(r"\n{3,}", "\n\n", new_content).rstrip() + "\n"
    if dry_run:
        return InstallResult(Action.WOULD_WRITE, target, "would strip managed block")
    _atomic_write(target, new_content)
    return InstallResult(Action.REMOVED_BLOCK, target)


def load_rule(rule_filename: str) -> str:
    """Read a bundled rule file from agent_delegate/rules/."""
    rules_dir = Path(__file__).parent / "rules"
    path = rules_dir / rule_filename
    if not path.exists():
        raise FileNotFoundError(f"rule file not bundled: {path}")
    return path.read_text(encoding="utf-8")
