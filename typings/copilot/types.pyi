"""Type stubs for copilot.types module.

These stubs are pyright-only namespace shims. There is no ``copilot.types``
module at runtime in SDK v0.3.0+ — runtime imports must go through
``amplifier_module_provider_github_copilot.sdk_adapter._imports`` (the
quarantined SDK boundary). Symbols whose runtime home moved (e.g.,
``PermissionRequestResult`` is now in ``copilot.session``) are stubbed in
their canonical sibling .pyi file, not here.

Field shapes were verified against the live SDK v0.3.0 source on 2026-05-12:

* ``LogLevel`` literals match ``copilot/client.py`` line 72.
* ``TelemetryConfig`` is a ``TypedDict(total=False)`` carrying OTEL
  fields (``otlp_endpoint``, ``file_path``, ``exporter_type``,
  ``source_name``, ``capture_content``) — NOT a dataclass with
  ``enabled: bool``. Mirrors ``copilot/client.py`` lines 84-96.
* ``SubprocessConfig`` carries ``session_fs: SessionFsConfig | None`` —
  see ``copilot/client.py`` line 150. ``SessionFsConfig`` itself is a
  TypedDict in ``copilot/session_fs_provider.py``; the provider does not
  construct one, so it is stubbed loosely as ``Any``.
* ``BlobAttachment`` is a ``TypedDict`` defined in ``copilot.session``
  with keys ``type``, ``data`` (base64 ``str``), ``mimeType`` (camelCase
  intentional), and optional ``displayName`` — NOT a dataclass with
  ``data: bytes``/``media_type: str``.
* ``ModelInfo`` carries only the fields the real SDK exposes:
  ``id``, ``name``, ``capabilities`` (nested object, required), ``policy``,
  ``billing``, ``supported_reasoning_efforts``, ``default_reasoning_effort``.
  Earlier stub versions invented ``family``/``vendor``/``context_window``/
  ``max_output_tokens``/``preview``/``is_default`` — those fields belong on
  ``amplifier_core.ModelInfo`` (kernel-facing) and ``CopilotModelInfo``
  (internal isolation), NOT on the SDK type.
* ``ModelPolicy.state`` is ``str`` (real runtime values include
  ``"enabled"``, ``"disabled"``, ``"unconfigured"`` — see
  ``copilot/client.py`` lines 477-493) and ``terms`` is required ``str``.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

LogLevel = Literal["none", "error", "warning", "info", "debug", "all"]


SessionFsConfig = Any
"""Opaque TypedDict from ``copilot.session_fs_provider``. The provider does
not construct one; this loose typing is enough for pyright to type-check
``SubprocessConfig`` references."""


class TelemetryConfig(TypedDict, total=False):
    """OpenTelemetry configuration for the Copilot CLI.

    Real SDK shape (``copilot/client.py`` lines 84-96) is a ``TypedDict``
    with all keys optional; providing the dict at all is what enables
    telemetry.
    """

    otlp_endpoint: str
    file_path: str
    exporter_type: str
    source_name: str
    capture_content: bool


@dataclass
class SubprocessConfig:
    """Configuration for SDK subprocess mode.

    Matches real SDK signature from ``copilot/client.py`` lines 100-159.
    """
    cli_path: str | None = None
    cli_args: list[str] = field(default_factory=list)
    cwd: str | None = None
    use_stdio: bool = True
    port: int = 0
    log_level: LogLevel = "info"
    env: dict[str, str] | None = None
    github_token: str | None = None
    use_logged_in_user: bool | None = None
    telemetry: TelemetryConfig | None = None
    session_fs: SessionFsConfig | None = None
    session_idle_timeout_seconds: int | None = None


class BlobAttachment(TypedDict, total=False):
    """Inline base64-encoded vision/blob attachment.

    Runtime home: ``copilot.session`` (TypedDict, not dataclass).
    ``mimeType`` is camelCase to match the SDK JSON wire format.
    """

    type: Literal["blob"]
    data: str
    mimeType: str
    displayName: str


# NOTE: ``PermissionRequestResult`` and ``PermissionRequestResultKind`` live
# in ``copilot.session`` at runtime in SDK v0.3.0+. The canonical stub is at
# ``typings/copilot/session.pyi``. Do NOT re-add a duplicate ``@dataclass``
# stub here.


@dataclass
class ModelInfo:
    """Information about an available model (SDK v0.3.0).

    Field set mirrors ``copilot/client.py`` lines 523-534 exactly. Note
    that ``capabilities`` is typed ``Any`` because the real SDK shape is a
    nested object (``capabilities.limits.max_context_window_tokens``,
    ``capabilities.supports.vision``); the provider's translation layer
    (``sdk_adapter/model_translation.py``) reads it via ``getattr`` and
    does not depend on a precise type.
    """

    id: str
    name: str
    capabilities: Any
    policy: ModelPolicy | None = None
    billing: Any | None = None
    supported_reasoning_efforts: list[str] | None = None
    default_reasoning_effort: str | None = None


@dataclass
class ModelPolicy:
    """Policy settings for a model (SDK v0.3.0).

    Real runtime ``state`` values include ``"enabled"``, ``"disabled"``,
    ``"unconfigured"`` — see ``copilot/client.py`` lines 477-493. ``terms``
    is non-optional in the SDK.
    """

    state: str = ""
    terms: str = ""


__all__ = [
    "BlobAttachment",
    "LogLevel",
    "ModelInfo",
    "ModelPolicy",
    "SessionFsConfig",
    "SubprocessConfig",
    "TelemetryConfig",
]
