"""Type stubs for ``copilot.client`` submodule (SDK v1.0.0b10).

SDK v1.0.0b7 removed ``SubprocessConfig`` — process-management options are
now direct kwargs on ``CopilotClient.__init__``. ``ReasoningEffort`` is
declared in ``copilot.session`` and re-exported from ``copilot.client``; the
live SDK exposes the identical ``Literal`` object at both module paths
(``copilot.session.ReasoningEffort is copilot.client.ReasoningEffort`` →
``True``). The drift test ``TestReasoningEffortReExportedAtSessionPath`` in
``tests/test_sdk_assumptions.py`` pins this invariant.

Verified against b10 ``copilot/client.py`` (citations inline).
"""

from collections.abc import Awaitable, Callable
from typing import Any, Literal

# CopilotSession is declared in ``session.pyi`` (canonical home matches the
# live SDK, b10 ``session.py:L1066``). Imported here so ``create_session``'s
# return type can be a real symbol instead of a forward-string annotation.
from copilot.session import CopilotSession as CopilotSession  # noqa: E402

# from b10 client.py:L110 — LogLevel is a Literal of six severity strings.
LogLevel = Literal["none", "error", "warning", "info", "debug", "all"]

ReasoningEffort = Literal["low", "medium", "high", "xhigh"]


# from b10 client.py:L645 — ModelPolicy fields are required positional
# (no default values in the SDK dataclass). The stub mirrors that exactly so
# call-site typos don't compile clean here while failing at runtime.
class ModelPolicy:
    state: str
    terms: str

    def __init__(self, state: str, terms: str) -> None: ...


# from b10 client.py:L670 — ModelBilling.multiplier is optional with
# default None; SDKSurface:MUST:7 pins the tolerance.
class ModelBilling:
    multiplier: float | None

    def __init__(self, multiplier: float | None = None) -> None: ...


class ModelCapabilities:
    """Opaque container; provider reads it via getattr in model_translation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class ModelLimits:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class ModelSupports:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class ModelVisionLimits:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


# from b10 client.py:L691 — ModelInfo is a dataclass with two required
# fields (id, name, capabilities) and four optional fields. The optional
# trio (policy, billing, reasoning effort) defaults to None / empty.
class ModelInfo:
    id: str
    name: str
    capabilities: ModelCapabilities
    policy: ModelPolicy | None
    billing: ModelBilling | None
    supported_reasoning_efforts: list[str] | None
    default_reasoning_effort: str | None

    def __init__(
        self,
        id: str,
        name: str,
        capabilities: ModelCapabilities,
        policy: ModelPolicy | None = None,
        billing: ModelBilling | None = None,
        supported_reasoning_efforts: list[str] | None = None,
        default_reasoning_effort: str | None = None,
    ) -> None: ...


class TelemetryConfig:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class RuntimeConnection:
    @staticmethod
    def for_uri(uri: str) -> RuntimeConnection: ...
    @staticmethod
    def for_stdio(*args: Any, **kwargs: Any) -> RuntimeConnection: ...


class ChildProcessRuntimeConnection(RuntimeConnection): ...
class StdioRuntimeConnection(RuntimeConnection): ...
class TcpRuntimeConnection(RuntimeConnection): ...
class UriRuntimeConnection(RuntimeConnection): ...


# from b10 client.py:L1073 — CopilotClient.__init__ is keyword-only.
# SDKSurface:MUST:8 pins the keyword set; a drift test in
# tests/test_sdk_assumptions.py fails loudly on shape change.
class CopilotClient:
    def __init__(
        self,
        *,
        connection: RuntimeConnection | None = None,
        working_directory: str | None = None,
        log_level: LogLevel = "info",
        env: dict[str, str] | None = None,
        github_token: str | None = None,
        base_directory: str | None = None,
        use_logged_in_user: bool | None = None,
        telemetry: TelemetryConfig | None = None,
        session_fs: Any | None = None,
        session_idle_timeout_seconds: int | None = None,
        enable_remote_sessions: bool = False,
        on_list_models: Callable[[], list[ModelInfo] | Awaitable[list[ModelInfo]]] | None = None,
        mode: str = "copilot-cli",
    ) -> None: ...
    async def create_session(
        self,
        *,
        on_permission_request: Any,
        model: str | None = None,
        reasoning_effort: str | None = None,
        tools: list[Any] | None = None,
        system_message: Any | None = None,
        available_tools: list[str] | None = None,
        excluded_tools: list[str] | None = None,
        model_capabilities: Any | None = None,
        streaming: bool | None = None,
        on_event: Callable[[Any], None] | None = None,
        # ``**kwargs`` admits the long tail of optional keywords (hooks,
        # mcp_servers, custom_agents, infinite_sessions, commands,
        # skill_directories, enable_config_discovery, ...). Runtime tests in
        # tests/test_sdk_assumptions.py and live-smoke coverage are the
        # source of truth for keyword spelling.
        **kwargs: Any,
    ) -> CopilotSession: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def __aenter__(self) -> CopilotClient: ...
    async def __aexit__(self, *args: Any) -> None: ...


# Lifecycle event helpers from b10 client.py (CloudSessionOptions:L123,
# PingResponse:L348, StopError:L382, GetStatusResponse:L405,
# GetAuthStatusResponse:L431, SessionContext:L754, lifecycle events:L882-L912+).
# Provider does not construct these directly; opaque Any keeps the membrane narrow.
CloudSessionOptions = Any
CloudSessionRepository = Any
GetAuthStatusResponse = Any
GetStatusResponse = Any
PingResponse = Any
RemoteSessionMode = Any
SessionBackgroundEvent = Any
SessionContext = Any
SessionCreatedEvent = Any
SessionDeletedEvent = Any
SessionForegroundEvent = Any
SessionLifecycleEvent = Any
SessionLifecycleEventBase = Any
SessionLifecycleEventMetadata = Any
SessionLifecycleEventType = Any
SessionLifecycleHandler = Any
SessionListFilter = Any
SessionMetadata = Any
SessionUpdatedEvent = Any
StopError = Any


__all__ = [
    "ChildProcessRuntimeConnection",
    "CloudSessionOptions",
    "CloudSessionRepository",
    "CopilotClient",
    "GetAuthStatusResponse",
    "GetStatusResponse",
    "LogLevel",
    "ModelBilling",
    "ModelCapabilities",
    "ModelInfo",
    "ModelLimits",
    "ModelPolicy",
    "ModelSupports",
    "ModelVisionLimits",
    "PingResponse",
    "ReasoningEffort",
    "RemoteSessionMode",
    "RuntimeConnection",
    "SessionBackgroundEvent",
    "SessionContext",
    "SessionCreatedEvent",
    "SessionDeletedEvent",
    "SessionForegroundEvent",
    "SessionLifecycleEvent",
    "SessionLifecycleEventBase",
    "SessionLifecycleEventMetadata",
    "SessionLifecycleEventType",
    "SessionLifecycleHandler",
    "SessionListFilter",
    "SessionMetadata",
    "SessionUpdatedEvent",
    "StdioRuntimeConnection",
    "StopError",
    "TcpRuntimeConnection",
    "TelemetryConfig",
    "UriRuntimeConnection",
]
