from .anthropic import AnthropicBackend
from .base import Backend, BackendError, ChatResult, Message
from .openai_compat import OpenAICompatBackend


def get_backend(name: str, **kwargs):
    """Factory — map backend name (from profile config) to instance."""
    if name == "openai-compat":
        return OpenAICompatBackend(**kwargs)
    if name == "anthropic":
        return AnthropicBackend(**kwargs)
    raise ValueError(f"unknown backend: {name!r}. Known: openai-compat, anthropic")


__all__ = [
    "AnthropicBackend",
    "Backend",
    "BackendError",
    "ChatResult",
    "Message",
    "OpenAICompatBackend",
    "get_backend",
]
