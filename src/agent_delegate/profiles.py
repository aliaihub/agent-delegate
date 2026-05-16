"""Profile config loader.

A profile binds a backend implementation to a default endpoint + model + auth.

Config file: ~/.agent-delegate/profiles.toml  (override with env AGENT_DELEGATE_CONFIG).

Example:

    default_profile = "ollama"

    [profiles.ollama]
    backend = "openai-compat"
    base_url = "http://localhost:11434/v1"
    default_model = "qwen3-coder:480b-cloud"
    # api_key_env optional; api_key inline is allowed but discouraged

    [profiles.lmstudio]
    backend = "openai-compat"
    base_url = "http://localhost:1234/v1"
    default_model = "qwen2.5-coder-32b-instruct"

    [profiles.openrouter]
    backend = "openai-compat"
    base_url = "https://openrouter.ai/api/v1"
    api_key_env = "OPENROUTER_API_KEY"
    default_model = "meta-llama/llama-3.3-70b-instruct"

    [profiles.haiku]
    backend = "anthropic"
    base_url = "https://api.anthropic.com/v1"
    api_key_env = "ANTHROPIC_API_KEY"
    default_model = "claude-haiku-4-5"
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path(os.environ.get(
    "AGENT_DELEGATE_HOME",
    str(Path.home() / ".agent-delegate"),
))
CONFIG_PATH = Path(os.environ.get(
    "AGENT_DELEGATE_CONFIG",
    str(CONFIG_DIR / "profiles.toml"),
))


@dataclass
class Profile:
    name: str
    backend: str  # "openai-compat" | "anthropic" | future
    base_url: str
    default_model: str
    api_key: Optional[str] = None     # resolved from env or inline
    api_key_env: Optional[str] = None
    extra_headers: Optional[dict] = None
    timeout: float = 120.0
    temperature: float = 0.2


DEFAULT_PROFILES: dict[str, dict] = {
    "ollama": {
        "backend": "openai-compat",
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen3-coder:480b-cloud",
    },
    "lmstudio": {
        "backend": "openai-compat",
        "base_url": "http://localhost:1234/v1",
        "default_model": "qwen2.5-coder-32b-instruct",
    },
    "openrouter": {
        "backend": "openai-compat",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
    "haiku": {
        "backend": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-haiku-4-5",
    },
}


def load_config() -> dict:
    """Read profiles.toml. If missing, return built-in defaults with default_profile=ollama."""
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("rb") as fh:
            return tomllib.load(fh)
    return {"default_profile": "ollama", "profiles": DEFAULT_PROFILES}


def list_profiles() -> list[str]:
    return list(load_config().get("profiles", {}).keys())


def get_profile(name: Optional[str] = None) -> Profile:
    """Resolve a profile by name. None → default_profile from config."""
    cfg = load_config()
    profiles = cfg.get("profiles", {})
    if not name:
        name = cfg.get("default_profile") or "ollama"
    if name not in profiles:
        raise KeyError(
            f"profile '{name}' not found. Available: {sorted(profiles.keys())}"
        )
    raw = profiles[name]
    api_key = raw.get("api_key")
    api_key_env = raw.get("api_key_env")
    if api_key_env and not api_key:
        api_key = os.environ.get(api_key_env)
    return Profile(
        name=name,
        backend=raw["backend"],
        base_url=raw["base_url"].rstrip("/"),
        default_model=raw["default_model"],
        api_key=api_key,
        api_key_env=api_key_env,
        extra_headers=raw.get("extra_headers"),
        timeout=float(raw.get("timeout", 120.0)),
        temperature=float(raw.get("temperature", 0.2)),
    )


def write_default_config() -> Path:
    """Create CONFIG_PATH with the bundled defaults. Safe — refuses to overwrite."""
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = ['default_profile = "ollama"', ""]
    for name, fields in DEFAULT_PROFILES.items():
        lines.append(f"[profiles.{name}]")
        for k, v in fields.items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            else:
                lines.append(f"{k} = {v}")
        lines.append("")
    CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote default config -> {CONFIG_PATH}", file=sys.stderr)
    return CONFIG_PATH
