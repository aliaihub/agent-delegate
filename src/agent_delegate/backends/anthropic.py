"""Anthropic backend using urllib."""

from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from typing import Iterable, Optional

from .base import BackendError, ChatResult, Message


class AnthropicBackend:
    name = "anthropic"

    def __init__(
        self,
        base_url: str = "https://api.anthropic.com/v1",
        api_key: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        anthropic_version: str = "2023-06-01",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.extra_headers = dict(extra_headers or {})
        self.anthropic_version = anthropic_version

    def chat(
        self,
        messages: Iterable[Message],
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        timeout: float = 120.0,
    ) -> ChatResult:
        url = f"{self.base_url}/messages"
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": self.anthropic_version,
        }
        if not self.api_key:
            raise BackendError("missing api key", backend=self.name)
        headers["x-api-key"] = self.api_key
        headers.update(self.extra_headers)

        messages_list = list(messages)
        system_messages = [m.content for m in messages_list if m.role == "system"]
        system = "\n\n".join(system_messages) if system_messages else None
        chat_messages = [
            {"role": m.role, "content": m.content}
            for m in messages_list
            if m.role in ("user", "assistant")
        ]

        body = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens if max_tokens is not None else 4096,
            "temperature": temperature,
            "stream": False,
        }
        if system:
            body["system"] = system

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                response_text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise BackendError(
                str(e),
                backend=self.name,
                status=e.code,
                body=e.read().decode("utf-8", "replace")[:2000],
            )
        except urllib.error.URLError as e:
            raise BackendError(
                f"network error: {e.reason}",
                backend=self.name,
            )
        elapsed = time.perf_counter() - start

        data = json.loads(response_text)
        content_blocks = data.get("content") or []
        content = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )
        usage = data.get("usage") or {}

        return ChatResult(
            content=content,
            model=data.get("model") or model,
            backend=self.name,
            prompt_tokens=int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0),
            completion_tokens=int(usage.get("output_tokens") or 0),
            cached_tokens=int(usage.get("cache_read_input_tokens") or 0),
            reasoning_tokens=0,
            total_duration_ms=int(elapsed * 1000),
            raw=data,
        )
