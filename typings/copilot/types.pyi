"""Type stubs for the ``copilot.types`` namespace shim (SDK v1.0.0b10).

There is no ``copilot.types`` module at runtime in SDK v0.3.0+ — runtime
imports must go through
``amplifier_module_provider_github_copilot.sdk_adapter._imports`` (the
quarantined SDK boundary). Symbols whose runtime home moved (e.g.,
``PermissionRequestResult`` is now in ``copilot.session``) are stubbed in
their canonical sibling ``.pyi`` file, not here.

Shapes verified against SDK v1.0.0b10 source:

* ``LogLevel`` literals match b10 ``client.py:L110``.
* ``TelemetryConfig`` is a ``TypedDict(total=False)`` carrying OTEL fields.
* ``BlobAttachment`` is a strict ``TypedDict`` defined in b10 ``session.py:L149``;
  ``type``, ``data``, ``mimeType`` are required, ``displayName`` is ``NotRequired``.
* ``ModelInfo`` carries fields ``id``, ``name``, ``capabilities``, ``policy``,
  ``billing``, ``supported_reasoning_efforts``, ``default_reasoning_effort``
  (b10 ``client.py:L691``).
* ``ModelPolicy`` fields are required (no defaults) per b10 ``client.py:L645``.
"""

from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

LogLevel = Literal["none", "error", "warning", "info", "debug", "all"]


SessionFsConfig = Any
"""Opaque TypedDict from ``copilot.session_fs_provider``. The provider does
not construct one; loose typing keeps the membrane narrow without losing
pyright coverage on adjacent imports."""


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


# from b10 session.py:L149 — BlobAttachment is a strict TypedDict.
# ``type``, ``data``, and ``mimeType`` are required; only ``displayName``
# is NotRequired. ``mimeType`` is camelCase to match the SDK wire format.
class BlobAttachment(TypedDict):
    """Inline base64-encoded vision/blob attachment."""

    type: Literal["blob"]
    data: str
    mimeType: str
    displayName: NotRequired[str]


@dataclass
class ModelInfo:
    """Information about an available model (SDK v1.0.0b10).

    Field set mirrors b10 ``client.py:L691`` exactly. ``capabilities``
    is typed ``Any`` because the real SDK shape is a nested object
    (``capabilities.limits.max_context_window_tokens``,
    ``capabilities.supports.vision``); the provider's translation layer
    (``sdk_adapter/model_translation.py``) reads it via ``getattr`` and does
    not depend on a precise type.
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
    """Policy settings for a model.

    Real runtime ``state`` values include ``"enabled"``, ``"disabled"``,
    ``"unconfigured"`` — see b10 ``client.py:L645``. Both fields are
    required positional in the SDK dataclass; no defaults.
    """

    state: str
    terms: str


__all__ = [
    "BlobAttachment",
    "LogLevel",
    "ModelInfo",
    "ModelPolicy",
    "SessionFsConfig",
    "TelemetryConfig",
]
