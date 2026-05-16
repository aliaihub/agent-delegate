"""Shared file-reading helpers used by `ask` and `write` commands."""

from __future__ import annotations

import json
import os
from glob import glob
from pathlib import Path
from typing import Iterable


MAX_FILE_BYTES = int(os.environ.get("AGENT_DELEGATE_MAX_FILE_BYTES", "750000"))
MAX_CORPUS_BYTES = int(os.environ.get("AGENT_DELEGATE_MAX_CORPUS_BYTES", "3000000"))
DEFAULT_EXCLUDE_DIRS = {".git", ".next", "build", "dist", "node_modules"}


def _is_glob(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


def _has_excluded_dir(path: Path) -> bool:
    return any(part in DEFAULT_EXCLUDE_DIRS for part in path.parts[:-1])


def _is_excluded_dir(path: Path) -> bool:
    return path.is_dir() and path.name in DEFAULT_EXCLUDE_DIRS


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_directory(path: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS)
        root_path = Path(root)
        for file_name in sorted(files):
            yield root_path / file_name


def expand_paths(paths: Iterable[str]) -> list[Path]:
    """Expand file, directory, and glob inputs into a deterministic file list."""
    files_by_resolved_path: dict[Path, Path] = {}
    for raw_path in paths:
        path = Path(raw_path)
        matches: list[Path]
        if _is_glob(raw_path):
            matches = [Path(match) for match in glob(raw_path, recursive=True)]
        else:
            matches = [path]

        if not matches:
            raise SystemExit(f"missing file: {raw_path}")

        for match in matches:
            if _has_excluded_dir(match) or _is_excluded_dir(match):
                continue
            if match.is_dir():
                for file_path in _iter_directory(match):
                    if file_path.is_file() and not _has_excluded_dir(file_path):
                        files_by_resolved_path.setdefault(file_path.resolve(), file_path)
                continue
            if match.is_file():
                files_by_resolved_path.setdefault(match.resolve(), match)
                continue
            if not _is_glob(raw_path):
                raise SystemExit(f"missing file: {raw_path}")

    return sorted(
        files_by_resolved_path.values(),
        key=lambda item: _display_path(item).casefold(),
    )


def read_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise SystemExit(f"missing file: {path}")
    size = file_path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise SystemExit(
            f"file too large for delegation: {path} "
            f"({size} bytes > {MAX_FILE_BYTES}). "
            "Trim or raise AGENT_DELEGATE_MAX_FILE_BYTES."
        )
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="utf-8", errors="replace")


def corpus(paths: Iterable[str]) -> str:
    """Render files as ``<file path="...">content</file>`` blocks joined by blank lines."""
    docs: list[str] = []
    total_size = 0
    for file_path in expand_paths(paths):
        size = file_path.stat().st_size
        total_size += size
        if total_size > MAX_CORPUS_BYTES:
            raise SystemExit(
                f"corpus too large for delegation: "
                f"{total_size} bytes > {MAX_CORPUS_BYTES}. "
                "Trim inputs or raise AGENT_DELEGATE_MAX_CORPUS_BYTES."
            )
        path = _display_path(file_path)
        docs.append(
            f"<file path={json.dumps(path)}>\n{read_text(str(file_path))}\n</file>"
        )
    return "\n\n".join(docs)
