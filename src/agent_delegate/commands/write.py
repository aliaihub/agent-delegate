"""write command — draft a boilerplate file from context + spec."""

from __future__ import annotations

import difflib
import sys
from pathlib import Path
from typing import Iterable

from ..backends import Backend, Message
from ..backends.base import BackendError
from ..output import json_error, json_success
from ..profiles import Profile
from ..usage_log import log_call
from ._corpus import corpus
from ._prompts import WRITE_SYSTEM


def strip_markdown_fences(content: str) -> str:
    """Strip one outer Markdown code fence when it wraps the whole response."""
    text = content.strip()
    lines = text.splitlines()
    if len(lines) < 2:
        return content

    if not lines[0].strip().startswith("```") or lines[-1].strip() != "```":
        return content

    return "\n".join(lines[1:-1])


def _resolve_target(target: str, target_root: str | None) -> tuple[Path | None, str | None]:
    target_path = Path(target)
    if target_root is None:
        return target_path, None

    root_path = Path(target_root).resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(root_path)
    except ValueError:
        return target_path, f"target escapes --target-root: {target_path} (root: {root_path})"
    return target_path, None


def _unified_diff(target_path: Path, content: str) -> str:
    old = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=str(target_path),
            tofile=str(target_path),
        )
    )


def run(
    backend: Backend,
    profile: Profile,
    model: str,
    context: Iterable[str],
    spec: str,
    target: str,
    force: bool = False,
    temperature: float = 0.1,
    json_output: bool = False,
    stdout: bool = False,
    strip_fences: bool = True,
    target_root: str | None = None,
    diff: bool = False,
) -> int:
    target_path = Path(target)
    if not stdout:
        target_path, target_error = _resolve_target(target, target_root)
        if target_error:
            message = target_error or f"target escapes --target-root: {target}"
            if json_output:
                json_error(
                    command="write",
                    profile=profile,
                    model=model,
                    message=message,
                    error_type="target_root_escape",
                    target=target,
                )
            else:
                print(message, file=sys.stderr)
            return 2

    if not stdout and target_path.exists() and not force:
        message = f"target exists, pass --force to overwrite: {target_path}"
        if json_output:
            json_error(
                command="write",
                profile=profile,
                model=model,
                message=message,
                error_type="target_exists",
                target=str(target_path),
            )
        else:
            print(message, file=sys.stderr)
        return 2

    try:
        corpus_text = corpus(context)
    except SystemExit as e:
        message = str(e)
        if json_output:
            json_error(
                command="write",
                profile=profile,
                model=model,
                message=message,
                error_type="corpus_error",
                target=str(target_path),
            )
        else:
            print(message, file=sys.stderr)
        return 2

    messages = [
        Message("system", WRITE_SYSTEM),
        Message("user", f"<context>\n{corpus_text}\n</context>"),
        Message("user", spec),
    ]
    try:
        result = backend.chat(
            messages, model, temperature=temperature, timeout=profile.timeout
        )
    except BackendError as e:
        if json_output:
            json_error(
                command="write",
                profile=profile,
                model=model,
                message=str(e),
                error_type="backend_error",
                target=str(target_path),
                backend_error=e,
            )
        else:
            print(f"delegation failed: {e}", file=sys.stderr)
        return 1

    log_call("write", profile, model, result, target=None if stdout else str(target_path))
    content = result.content
    if strip_fences:
        content = strip_markdown_fences(content)
    content = content.rstrip() + "\n"

    if stdout:
        if json_output:
            json_success(
                command="write",
                profile=profile,
                model=model,
                content=content,
                target=str(target_path),
                usage=result,
            )
        else:
            print(content, end="")
        return 0

    if diff and not json_output:
        print(_unified_diff(target_path, content), end="")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    if json_output:
        json_success(
            command="write",
            profile=profile,
            model=model,
            content=content,
            target=str(target_path),
            usage=result,
        )
    else:
        print(f"wrote {target_path}")
    return 0
