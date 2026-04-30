"""Type stubs for github-copilot-sdk (imported as 'copilot').

These stubs satisfy pyright strict mode when the SDK is not installed.
The actual SDK types come from the github-copilot-sdk package at runtime.
"""

from typing import Any, AsyncIterator

class CopilotClient:
    """Copilot SDK client for accessing LLM APIs."""
    
    def __init__(self, config: Any = None) -> None: ...
    
    @classmethod
    def from_subprocess(cls, config: Any = None) -> "CopilotClient": ...
    
    async def session(
        self,
        *,
        model: str | None = None,
        system_message: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "CopilotSession": ...
    
    async def create_session(self, **kwargs: Any) -> "CopilotSession": ...
    
    async def list_models(self) -> list[Any]: ...
    
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> "CopilotClient": ...
    async def __aexit__(self, *args: Any) -> None: ...


class CopilotSession:
    """SDK session for streaming completions."""
    
    async def send(
        self,
        prompt: str,
        *,
        tools: list[Any] | None = None,
        attachments: list[Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]: ...
    
    async def send_and_wait(
        self,
        prompt: str,
        *,
        timeout: float | None = None,
        tools: list[Any] | None = None,
        attachments: list[Any] | None = None,
        **kwargs: Any,
    ) -> Any: ...
    
    async def disconnect(self) -> None: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> "CopilotSession": ...
    async def __aexit__(self, *args: Any) -> None: ...


class ModelLimitsOverride:
    """Per-session token limit overrides (SDK v0.3.0).

    Forwarded by the provider to honor ChatRequest.max_tokens via
    ModelCapabilitiesOverride.limits.max_output_tokens.
    """

    max_prompt_tokens: int | None
    max_output_tokens: int | None
    max_context_window_tokens: int | None
    vision: Any | None

    def __init__(
        self,
        *,
        max_prompt_tokens: int | None = None,
        max_output_tokens: int | None = None,
        max_context_window_tokens: int | None = None,
        vision: Any | None = None,
    ) -> None: ...


class ModelCapabilitiesOverride:
    """Per-session capability overrides (SDK v0.3.0)."""

    supports: Any | None
    limits: ModelLimitsOverride | None

    def __init__(
        self,
        *,
        supports: Any | None = None,
        limits: ModelLimitsOverride | None = None,
    ) -> None: ...


__all__ = [
    "CopilotClient",
    "CopilotSession",
    "ModelCapabilitiesOverride",
    "ModelLimitsOverride",
]
