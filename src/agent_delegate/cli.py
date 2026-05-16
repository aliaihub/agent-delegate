"""Top-level CLI dispatcher.

Resolves profile + backend, then delegates to subcommand modules.

Subcommands:
    ask          — answer a question from one or more files
    write        — draft a boilerplate file
    summarize    — condense stdin
    profiles     — list / show / set-default profiles
    install      — inject rule snippets into AI tool configs
    uninstall    — strip injected rule blocks
    status       — show install state + active profile
    doctor       — ping configured profiles, check API keys
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from . import __version__
from .backends import get_backend
from .output import json_error
from .profiles import (
    get_profile,
    list_profiles,
    load_config,
    write_default_config,
)


def _make_backend(profile):
    """Instantiate the backend implementation for a resolved Profile."""
    kwargs = {"base_url": profile.base_url}
    if profile.api_key:
        kwargs["api_key"] = profile.api_key
    if profile.extra_headers:
        kwargs["extra_headers"] = profile.extra_headers
    return get_backend(profile.backend, **kwargs)


def _resolve(args: argparse.Namespace):
    """Common preamble for ask/write/summarize: profile + model + backend."""
    profile = get_profile(args.profile)
    model = args.model or profile.default_model
    backend = _make_backend(profile)
    return profile, model, backend


def _cmd_ask(args: argparse.Namespace) -> int:
    from .commands import ask
    try:
        profile, model, backend = _resolve(args)
    except (KeyError, ValueError) as e:
        if args.json:
            json_error(
                command="ask",
                profile=args.profile,
                model=args.model,
                message=str(e),
                error_type="resolve_error",
            )
        else:
            print(str(e), file=sys.stderr)
        return 2
    return ask.run(
        backend, profile, model,
        paths=args.paths, question=args.question,
        temperature=args.temperature, json_output=args.json,
    )


def _cmd_write(args: argparse.Namespace) -> int:
    from .commands import write
    if args.target is None and not args.stdout:
        message = "--target is required unless --stdout is used"
        if args.json:
            json_error(
                command="write",
                profile=args.profile,
                model=args.model,
                message=message,
                error_type="missing_target",
            )
        else:
            print(message, file=sys.stderr)
        return 2
    try:
        profile, model, backend = _resolve(args)
    except (KeyError, ValueError) as e:
        if args.json:
            json_error(
                command="write",
                profile=args.profile,
                model=args.model,
                message=str(e),
                error_type="resolve_error",
                target=args.target,
            )
        else:
            print(str(e), file=sys.stderr)
        return 2
    return write.run(
        backend, profile, model,
        context=args.context, spec=args.spec, target=args.target or "-",
        force=args.force, temperature=args.temperature, json_output=args.json,
        stdout=args.stdout, strip_fences=args.strip_fences,
        target_root=args.target_root, diff=args.diff,
    )


def _cmd_summarize(args: argparse.Namespace) -> int:
    from .commands import summarize
    try:
        profile, model, backend = _resolve(args)
    except (KeyError, ValueError) as e:
        if args.json:
            json_error(
                command="summarize",
                profile=args.profile,
                model=args.model,
                message=str(e),
                error_type="resolve_error",
            )
        else:
            print(str(e), file=sys.stderr)
        return 2
    return summarize.run(
        backend, profile, model, temperature=args.temperature, json_output=args.json,
    )


def _cmd_profiles(args: argparse.Namespace) -> int:
    sub = args.profiles_sub
    if sub == "list":
        cfg = load_config()
        default = cfg.get("default_profile", "")
        for name in list_profiles():
            marker = " (default)" if name == default else ""
            print(f"{name}{marker}")
        return 0
    if sub == "show":
        try:
            p = get_profile(args.name)
        except KeyError as e:
            print(str(e), file=sys.stderr)
            return 2
        print(f"name           {p.name}")
        print(f"backend        {p.backend}")
        print(f"base_url       {p.base_url}")
        print(f"default_model  {p.default_model}")
        print(f"api_key_env    {p.api_key_env or '-'}")
        print(f"api_key set    {'yes' if p.api_key else 'no'}")
        print(f"timeout        {p.timeout}")
        return 0
    if sub == "init":
        path = write_default_config()
        print(f"config at {path}")
        return 0
    print("unknown profiles subcommand", file=sys.stderr)
    return 2


def _cmd_status(args: argparse.Namespace) -> int:
    from .detect import detect_all
    from .install import _BLOCK_RE, _read

    cfg = load_config()
    default = cfg.get("default_profile", "")
    print(f"agent-delegate v{__version__}")
    print(f"default profile: {default}")
    print(f"profiles:        {', '.join(list_profiles())}")
    if default:
        try:
            p = get_profile(default)
            print(f"default backend: {p.backend}")
            print(f"default model:   {p.default_model}")
            print(f"default host:    {p.base_url}")
        except KeyError:
            print("default backend: unavailable")
            print("default model:   unavailable")
            print("default host:    unavailable")
    print()
    print("install state:")
    for d in detect_all():
        if not d.target.auto_install:
            print(f"  {d.target.slug:18s} (manual paste) — see `agent-delegate install --print {d.target.slug}`")
            continue
        if not d.found:
            print(f"  {d.target.slug:18s} config directory not found — {d.target.config_file.parent}")
            continue
        existing = _read(d.config_path) or ""
        installed = bool(_BLOCK_RE.search(existing))
        marker = "rule installed" if installed else "rule not installed"
        print(f"  {d.target.slug:18s} {marker} — {d.config_path}")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Lightweight probe of each profile — just checks API key presence + connectivity."""
    import urllib.error
    import urllib.request

    rc = 0
    for name in list_profiles():
        try:
            p = get_profile(name)
        except KeyError as e:
            print(f"{name:15s} ERROR {e}")
            rc = 1
            continue
        key_ok = "n/a" if not p.api_key_env else ("set" if p.api_key else "MISSING")
        # Probe base_url with a HEAD-ish GET; many endpoints return 401 or 404,
        # which still proves the host is reachable.
        try:
            req = urllib.request.Request(p.base_url, method="GET")
            urllib.request.urlopen(req, timeout=3.0)
            reach = "reachable"
        except urllib.error.HTTPError as e:
            reach = f"reachable ({e.code})"
        except urllib.error.URLError as e:
            reach = f"unreachable ({e.reason})"
            rc = 1
        print(f"{name:15s} backend={p.backend:14s} key={key_ok:7s} {reach}  -> {p.base_url}")
    return rc


def _cmd_ledger(args: argparse.Namespace) -> int:
    from pathlib import Path

    from .ledger import print_text, read_entries, recent_entries, summarize_entries
    from .output import json_error, json_success

    path = Path(args.log) if args.log else None
    entries = read_entries(path)
    if not entries:
        message = "usage log not found or contains no delegation calls"
        if args.json:
            json_error(
                command="ledger",
                profile=None,
                model=None,
                message=message,
                error_type="empty_ledger",
            )
        else:
            print(message, file=sys.stderr)
        return 2

    if args.json:
        content = {
            "entries": recent_entries(entries, args.limit),
            "summary": summarize_entries(entries),
        }
        json_success(
            command="ledger",
            profile=None,
            model="-",
            content=content,
        )
    else:
        print_text(entries, limit=args.limit)
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    from .detect import detect_all, detect_by_slug
    from .install import inject_block, load_rule

    # Print-only mode: just show the snippet for one tool and exit.
    if args.print:
        d = detect_by_slug(args.print)
        if not d:
            print(f"unknown tool: {args.print}", file=sys.stderr)
            return 2
        print(load_rule(d.target.rule_filename))
        return 0

    targets = detect_all()
    if args.tool:
        wanted = set(args.tool.split(","))
        targets = [t for t in targets if t.target.slug in wanted]
        if not targets:
            print(f"no tools matched: {args.tool}", file=sys.stderr)
            return 2

    rc = 0
    for d in targets:
        rule = load_rule(d.target.rule_filename)
        if not d.target.auto_install:
            print(f"\n=== {d.target.display} ({d.target.slug}) — copy/paste below ===")
            print(rule)
            continue
        if not d.found:
            print(f"{d.target.slug:18s} SKIPPED — tool not detected ({d.target.config_file.parent} missing)")
            continue
        result = inject_block(d.config_path, rule, dry_run=args.dry_run)
        print(f"{d.target.slug:18s} {result.action.value:18s} {result.target}" +
              (f"  ({result.detail})" if result.detail else ""))
    return rc


def _cmd_uninstall(args: argparse.Namespace) -> int:
    from .detect import detect_all
    from .install import strip_block

    targets = detect_all()
    if args.tool:
        wanted = set(args.tool.split(","))
        targets = [t for t in targets if t.target.slug in wanted]

    rc = 0
    for d in targets:
        if not d.target.auto_install:
            print(f"{d.target.slug:18s} (manual paste — remove block by hand from desktop app)")
            continue
        if not d.config_exists:
            print(f"{d.target.slug:18s} skipped — no config file at {d.config_path}")
            continue
        result = strip_block(d.config_path, dry_run=args.dry_run)
        print(f"{d.target.slug:18s} {result.action.value:18s} {result.target}" +
              (f"  ({result.detail})" if result.detail else ""))
    return rc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="agent-delegate",
        description="Route low-reasoning tasks to a cheap or local LLM backend.",
    )
    p.add_argument("--version", action="version", version=f"agent-delegate {__version__}")
    p.add_argument("--profile", default=None,
                   help="profile name from profiles.toml (default: profiles.toml's default_profile)")
    p.add_argument("--model", default=None,
                   help="override the profile's default model")
    p.add_argument("--temperature", type=float, default=0.1)

    sub = p.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="answer a question from one or more files")
    ask.add_argument("--paths", nargs="+", required=True)
    ask.add_argument("--question", required=True)
    ask.add_argument("--json", action="store_true",
                     help="emit a stable JSON envelope instead of text output")
    ask.set_defaults(func=_cmd_ask)

    write = sub.add_parser("write", help="draft a boilerplate file")
    write.add_argument("--context", nargs="+", required=True)
    write.add_argument("--spec", required=True)
    write.add_argument("--target")
    write.add_argument("--force", action="store_true")
    write.add_argument("--json", action="store_true",
                       help="emit a stable JSON envelope instead of text output")
    write.add_argument("--stdout", action="store_true",
                       help="print generated content instead of writing --target")
    write.add_argument("--strip-fences", dest="strip_fences", action="store_true",
                       default=True,
                       help="strip one outer Markdown code fence from model output (default)")
    write.add_argument("--no-strip-fences", dest="strip_fences", action="store_false",
                       help="preserve model output exactly, including Markdown fences")
    write.add_argument("--target-root", default=None,
                       help="refuse to write when --target resolves outside this directory")
    write.add_argument("--diff", action="store_true",
                       help="print a unified diff before writing")
    write.set_defaults(func=_cmd_write)

    summarize = sub.add_parser("summarize", help="condense stdin")
    summarize.add_argument("--json", action="store_true",
                           help="emit a stable JSON envelope instead of text output")
    summarize.set_defaults(func=_cmd_summarize)

    profiles = sub.add_parser("profiles", help="manage profiles")
    profiles_sub = profiles.add_subparsers(dest="profiles_sub", required=True)
    profiles_sub.add_parser("list", help="list profiles")
    show = profiles_sub.add_parser("show", help="show one profile's resolved config")
    show.add_argument("name")
    profiles_sub.add_parser("init", help="write profiles.toml with the bundled defaults")
    profiles.set_defaults(func=_cmd_profiles)

    status = sub.add_parser("status", help="show package version + active profile")
    status.set_defaults(func=_cmd_status)

    doctor = sub.add_parser("doctor", help="probe each profile for reachability + auth")
    doctor.set_defaults(func=_cmd_doctor)

    ledger = sub.add_parser("ledger", help="show delegated worker calls from the usage log")
    ledger.add_argument("--json", action="store_true",
                        help="emit a stable JSON envelope instead of text output")
    ledger.add_argument("--limit", type=int, default=20,
                        help="number of recent calls to show in the entries list (default: 20)")
    ledger.add_argument("--log", default=None,
                        help="explicit JSONL usage log path; defaults to AGENT_DELEGATE_LOG/LOG_DIR")
    ledger.set_defaults(func=_cmd_ledger)

    install = sub.add_parser("install", help="inject rule snippets into AI tool configs")
    install.add_argument("--dry-run", action="store_true",
                         help="show what would be written, don't touch files")
    install.add_argument("--tool", default=None,
                         help="comma-separated subset: claude-code,codex-cli,claude-desktop,codex-app")
    install.add_argument("--print", default=None, metavar="TOOL",
                         help="print one tool's rule snippet to stdout and exit")
    install.set_defaults(func=_cmd_install)

    uninstall = sub.add_parser("uninstall", help="strip injected rule blocks")
    uninstall.add_argument("--dry-run", action="store_true")
    uninstall.add_argument("--tool", default=None,
                           help="comma-separated subset (default: all)")
    uninstall.set_defaults(func=_cmd_uninstall)

    return p


def _force_utf8_stdio() -> None:
    """Make stdout/stderr tolerate unicode on Windows consoles (cp1252 default)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main(argv: Optional[list[str]] = None) -> int:
    _force_utf8_stdio()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
