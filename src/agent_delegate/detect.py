"""Detect installed AI tools by looking for their config directories on disk.

Cross-platform via pathlib. Returns a dict keyed by tool slug.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ToolTarget:
    slug: str           # short id used on the CLI: --tool claude-code
    display: str        # human-readable name
    config_file: Path   # where the rule block goes (or empty Path for desktop apps)
    auto_install: bool  # True = installer writes to disk; False = print snippet only
    rule_filename: str  # which rules/*.md to inject


def _home() -> Path:
    return Path.home()


def _tools_catalog() -> list[ToolTarget]:
    h = _home()
    return [
        ToolTarget(
            slug="claude-code",
            display="Claude Code (CLI)",
            config_file=h / ".claude" / "CLAUDE.md",
            auto_install=True,
            rule_filename="claude_code.md",
        ),
        ToolTarget(
            slug="codex-cli",
            display="Codex CLI",
            # Codex renamed instructions.md → AGENTS.md. Prefer AGENTS.md;
            # the installer falls back to instructions.md if only that exists.
            config_file=h / ".codex" / "AGENTS.md",
            auto_install=True,
            rule_filename="codex_cli.md",
        ),
        ToolTarget(
            slug="claude-desktop",
            display="Claude desktop (project instructions)",
            config_file=Path(),
            auto_install=False,
            rule_filename="claude_desktop.md",
        ),
        ToolTarget(
            slug="codex-app",
            display="Codex web (project instructions)",
            config_file=Path(),
            auto_install=False,
            rule_filename="codex_app.md",
        ),
    ]


def _codex_config_path(target: ToolTarget) -> Path:
    """Resolve Codex CLI config path: prefer AGENTS.md, fall back to legacy instructions.md."""
    if target.slug != "codex-cli":
        return target.config_file
    legacy = target.config_file.parent / "instructions.md"
    if not target.config_file.exists() and legacy.exists():
        return legacy
    return target.config_file


@dataclass
class DetectedTool:
    target: ToolTarget
    found: bool
    config_path: Path
    config_exists: bool


def detect_all() -> list[DetectedTool]:
    """Probe each known tool. `found` = parent dir exists. `config_exists` = file exists."""
    results: list[DetectedTool] = []
    for t in _tools_catalog():
        if not t.auto_install:
            # Desktop apps — always "found", they print regardless.
            results.append(DetectedTool(t, True, Path(), False))
            continue
        cfg = _codex_config_path(t)
        parent_exists = cfg.parent.exists()
        results.append(DetectedTool(
            target=t,
            found=parent_exists,
            config_path=cfg,
            config_exists=cfg.exists(),
        ))
    return results


def detect_by_slug(slug: str) -> Optional[DetectedTool]:
    for d in detect_all():
        if d.target.slug == slug:
            return d
    return None
