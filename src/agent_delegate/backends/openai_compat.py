"""OpenAI-compatible backend using urllib."""

from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from typing import Iterable, Optional

from .base import BackendError, ChatResult, Message


class OpenAICompatBackend:
    name = "openai-compat"

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.extra_headers = dict(extra_headers or {})

    def chat(
        self,
        messages: Iterable[Message],
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        timeout: float = 120.0,
    ) -> ChatResult:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)

        body = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

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
        choices = data.get("choices") or []
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message") or {}
        content = message.get("content", "")
        usage = data.get("usage") or {}

        return ChatResult(
            content=content,
            model=data.get("model") or model,
            backend=self.name,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            cached_tokens=int(((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)),
            reasoning_tokens=int(((usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)),
            total_duration_ms=int(elapsed * 1000),
            raw=data,
        )
