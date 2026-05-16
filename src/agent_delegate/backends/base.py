"""Backend protocol — every provider adapter implements this."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol, runtime_checkable


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatResult:
    """Normalized response from any backend."""
    content: str
    model: str
    backend: str
    # Raw counts in the underlying provider's terms — caller normalizes for token-meter log
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    total_duration_ms: Optional[int] = None
    raw: dict = field(default_factory=dict)  # provider-native response, for debugging


@runtime_checkable
class Backend(Protocol):
    """Adapter interface. Implementations live in agent_delegate/backends/*.py."""

    name: str  # short identifier, e.g. "openai-compat", "anthropic"

    def chat(
        self,
        messages: Iterable[Message],
        model: str,
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        timeout: float = 120.0,
    ) -> ChatResult:
        """Send a chat-completion request. Raise BackendError on failure."""
        ...


class BackendError(Exception):
    """Raised by backends on any API / network / auth failure. Carries provider context."""

    def __init__(self, message: str, *, backend: str = "", status: Optional[int] = None,
                 body: Optional[str] = None) -> None:
        super().__init__(message)
        self.backend = backend
        self.status = status
        self.body = body
