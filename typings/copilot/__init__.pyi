"""Type stubs for github-copilot-sdk (imported as ``copilot``) — v1.0.0b10.

Mirrors the public API surface of github-copilot-sdk v1.0.0b10. Only the symbols
the provider actually uses are stubbed in detail; the long tail of re-exports
(canvas, hooks, lifecycle events, MCP server configs, tool helpers) is
declared as ``Any`` so the membrane stays narrow without losing pyright
coverage on imports through ``sdk_adapter._imports``.

Verified against b10 ``copilot/__init__.py:L1-L277`` and ``copilot/client.py``.
"""

from typing import Any

# CopilotSession canonical home is ``copilot.session`` (b10
# ``session.py:L1066``); re-export from the root for the import path that
# the provider's membrane uses. Keeping the class declaration in
# ``session.pyi`` lets ``client.pyi`` reference it for ``create_session``'s
# return type without a stub import cycle.
from copilot.session import CopilotSession as CopilotSession  # noqa: E402

class ModelVisionLimitsOverride:
    supported_media_types: list[str] | None
    max_prompt_images: int | None
    max_prompt_image_size: int | None

    def __init__(
        self,
        *,
        supported_media_types: list[str] | None = None,
        max_prompt_images: int | None = None,
        max_prompt_image_size: int | None = None,
    ) -> None: ...

class ModelSupportsOverride:
    vision: bool | None
    reasoning_effort: bool | None

    def __init__(
        self,
        *,
        vision: bool | None = None,
        reasoning_effort: bool | None = None,
    ) -> None: ...

class ModelLimitsOverride:
    max_prompt_tokens: int | None
    max_output_tokens: int | None
    max_context_window_tokens: int | None
    vision: ModelVisionLimitsOverride | None

    def __init__(
        self,
        *,
        max_prompt_tokens: int | None = None,
        max_output_tokens: int | None = None,
        max_context_window_tokens: int | None = None,
        vision: ModelVisionLimitsOverride | None = None,
    ) -> None: ...

class ModelCapabilitiesOverride:
    supports: ModelSupportsOverride | None
    limits: ModelLimitsOverride | None

    def __init__(
        self,
        *,
        supports: ModelSupportsOverride | None = None,
        limits: ModelLimitsOverride | None = None,
    ) -> None: ...

# CopilotClient is declared in copilot.client and re-exported at the package
# root by b10 ``__init__.py:L23-L63``. The stub for the constructor lives in
# ``client.pyi`` so the surface stays close to its source-of-truth module.
from copilot.client import CopilotClient as CopilotClient  # noqa: E402

# Re-exports from copilot.client (b10 __init__.py:L23-L63).
ChildProcessRuntimeConnection = Any
CloudSessionOptions = Any
CloudSessionRepository = Any
GetAuthStatusResponse = Any
GetStatusResponse = Any
LogLevel = Any
ModelBilling = Any
ModelCapabilities = Any
ModelInfo = Any
ModelLimits = Any
ModelPolicy = Any
ModelSupports = Any
ModelVisionLimits = Any
PingResponse = Any
RemoteSessionMode = Any
RuntimeConnection = Any
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
StdioRuntimeConnection = Any
StopError = Any
TcpRuntimeConnection = Any
TelemetryConfig = Any
UriRuntimeConnection = Any

# Re-exports from copilot.session (b10 __init__.py:L69-L130).
AutoModeSwitchHandler = Any
AutoModeSwitchRequest = Any
AutoModeSwitchResponse = Any
CommandContext = Any
CommandDefinition = Any
CreateSessionFsHandler = Any
ElicitationContext = Any
ElicitationHandler = Any
ElicitationParams = Any
ElicitationResult = Any
ErrorOccurredHandler = Any
ErrorOccurredHookInput = Any
ErrorOccurredHookOutput = Any
ExitPlanModeHandler = Any
ExitPlanModeRequest = Any
ExitPlanModeResult = Any
InfiniteSessionConfig = Any
InputOptions = Any
MCPHTTPServerConfig = Any
MCPServerConfig = Any
MCPStdioServerConfig = Any
PermissionHandler = Any
# PermissionNoResult is declared in copilot.session (b10 session.py:L256-L266 —
# @dataclass with one defaulted ``kind`` field). Re-exported from the package
# root by b10 ``__init__.py``; mirror that here so ``copilot.PermissionNoResult``
# resolves to the real type instead of ``Any``.
from copilot.session import PermissionNoResult as PermissionNoResult  # noqa: E402, I001
# PermissionRequestResult is the type alias `PermissionDecision | PermissionNoResult`
# declared in copilot.session (b10 session.py:L275) and re-exported at the package
# root by b10 ``__init__.py:L94``. Re-export the precise alias from the session stub
# so pyright resolves the discriminated union at consumer sites instead of `Any`.
from copilot.session import PermissionRequestResult as PermissionRequestResult  # noqa: E402, I001

PostToolUseHandler = Any
PostToolUseFailureHandler = Any
PostToolUseFailureHookInput = Any
PostToolUseFailureHookOutput = Any
PostToolUseHookInput = Any
PostToolUseHookOutput = Any
PreMcpToolCallHandler = Any
PreMcpToolCallHookInput = Any
PreMcpToolCallHookOutput = Any
PreToolUseHandler = Any
PreToolUseHookInput = Any
PreToolUseHookOutput = Any
ProviderConfig = Any
SessionCapabilities = Any
SessionEndHandler = Any
SessionEndHookInput = Any
SessionEndHookOutput = Any
SessionEventHandler = Any
SessionFsCapabilities = Any
SessionFsConfig = Any
SessionHooks = Any
SessionStartHandler = Any
SessionStartHookInput = Any
SessionStartHookOutput = Any
SessionUiApi = Any
SessionUiCapabilities = Any
SystemMessageConfig = Any
UserInputHandler = Any
UserInputRequest = Any
UserInputResponse = Any
UserPromptSubmittedHandler = Any
UserPromptSubmittedHookInput = Any
UserPromptSubmittedHookOutput = Any

# Re-exports from copilot.canvas (b10 __init__.py:L12-L22).
CanvasAction = Any
CanvasDeclaration = Any
CanvasError = Any
CanvasHandler = Any
CanvasHostContext = Any
CanvasHostContextCapabilities = Any
CanvasJsonSchema = Any
ExtensionInfo = Any
OpenCanvasInstance = Any

# Re-exports from copilot.generated.session_events (b10 __init__.py:L64-L68).
PermissionRequest = Any
SessionEvent = Any
SessionEventType = Any

# Re-exports from copilot._mode (b10 __init__.py:L7-L11).
BUILTIN_TOOLS_ISOLATED: Any
CopilotClientMode = Any
ToolSet = Any

# Re-exports from copilot.session_fs_provider (b10 __init__.py:L131-L137).
SessionFsFileInfo = Any
SessionFsProvider = Any
SessionFsSqliteProvider = Any
SessionFsSqliteQueryResult = Any
create_session_fs_adapter: Any

# Re-exports from copilot.tools (b10 __init__.py:L138-L146).
Tool = Any
ToolBinaryResult = Any
ToolInvocation = Any
ToolResult = Any
ToolResultType = Any
convert_mcp_call_tool_result: Any
define_tool: Any

# Re-exports added in b10 — both appear in copilot.__all__ (b10
# __init__.py:L150+) and are stubbed as opaque Any to keep the membrane
# narrow; provider does not construct or inspect these directly.
LargeToolOutputConfig = Any
ReasoningSummary = Any


__all__ = [
    "AutoModeSwitchHandler",
    "AutoModeSwitchRequest",
    "AutoModeSwitchResponse",
    "BUILTIN_TOOLS_ISOLATED",
    "CanvasAction",
    "CanvasDeclaration",
    "CanvasError",
    "CanvasHandler",
    "CanvasHostContext",
    "CanvasHostContextCapabilities",
    "CanvasJsonSchema",
    "ChildProcessRuntimeConnection",
    "CloudSessionOptions",
    "CloudSessionRepository",
    "CommandContext",
    "CommandDefinition",
    "CopilotClient",
    "CopilotClientMode",
    "CopilotSession",
    "CreateSessionFsHandler",
    "ElicitationContext",
    "ElicitationHandler",
    "ElicitationParams",
    "ElicitationResult",
    "ErrorOccurredHandler",
    "ErrorOccurredHookInput",
    "ErrorOccurredHookOutput",
    "ExitPlanModeHandler",
    "ExitPlanModeRequest",
    "ExitPlanModeResult",
    "ExtensionInfo",
    "GetAuthStatusResponse",
    "GetStatusResponse",
    "InfiniteSessionConfig",
    "InputOptions",
    "LargeToolOutputConfig",
    "LogLevel",
    "MCPHTTPServerConfig",
    "MCPServerConfig",
    "MCPStdioServerConfig",
    "ModelBilling",
    "ModelCapabilities",
    "ModelCapabilitiesOverride",
    "ModelInfo",
    "ModelLimits",
    "ModelLimitsOverride",
    "ModelPolicy",
    "ModelSupports",
    "ModelSupportsOverride",
    "ModelVisionLimits",
    "ModelVisionLimitsOverride",
    "OpenCanvasInstance",
    "PermissionHandler",
    "PermissionNoResult",
    "PermissionRequest",
    "PermissionRequestResult",
    "PingResponse",
    "PostToolUseFailureHandler",
    "PostToolUseFailureHookInput",
    "PostToolUseFailureHookOutput",
    "PostToolUseHandler",
    "PostToolUseHookInput",
    "PostToolUseHookOutput",
    "PreMcpToolCallHandler",
    "PreMcpToolCallHookInput",
    "PreMcpToolCallHookOutput",
    "PreToolUseHandler",
    "PreToolUseHookInput",
    "PreToolUseHookOutput",
    "ProviderConfig",
    "ReasoningSummary",
    "RemoteSessionMode",
    "RuntimeConnection",
    "SessionBackgroundEvent",
    "SessionCapabilities",
    "SessionContext",
    "SessionCreatedEvent",
    "SessionDeletedEvent",
    "SessionEndHandler",
    "SessionEndHookInput",
    "SessionEndHookOutput",
    "SessionEvent",
    "SessionEventHandler",
    "SessionEventType",
    "SessionForegroundEvent",
    "SessionFsCapabilities",
    "SessionFsConfig",
    "SessionFsFileInfo",
    "SessionFsProvider",
    "SessionFsSqliteProvider",
    "SessionFsSqliteQueryResult",
    "SessionHooks",
    "SessionLifecycleEvent",
    "SessionLifecycleEventBase",
    "SessionLifecycleEventMetadata",
    "SessionLifecycleEventType",
    "SessionLifecycleHandler",
    "SessionListFilter",
    "SessionMetadata",
    "SessionStartHandler",
    "SessionStartHookInput",
    "SessionStartHookOutput",
    "SessionUiApi",
    "SessionUiCapabilities",
    "SessionUpdatedEvent",
    "StdioRuntimeConnection",
    "StopError",
    "SystemMessageConfig",
    "TcpRuntimeConnection",
    "TelemetryConfig",
    "Tool",
    "ToolBinaryResult",
    "ToolInvocation",
    "ToolResult",
    "ToolResultType",
    "ToolSet",
    "UriRuntimeConnection",
    "UserInputHandler",
    "UserInputRequest",
    "UserInputResponse",
    "UserPromptSubmittedHandler",
    "UserPromptSubmittedHookInput",
    "UserPromptSubmittedHookOutput",
    "convert_mcp_call_tool_result",
    "create_session_fs_adapter",
    "define_tool",
]
