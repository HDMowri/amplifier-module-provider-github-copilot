"""SDK Import Quarantine.

All SDK imports are isolated here per sdk-boundary.md contract.

This enables:
- Easy SDK version tracking (all imports in one place)
- Single point for SDK compatibility shims
- Clear boundary for membrane violations
- Import-time failure if SDK not installed

Contract: contracts/sdk-boundary.md
"""

from __future__ import annotations

import os
from typing import Any

# Single source of truth for pytest detection (defined in _platform.py).
from .._platform import is_pytest_running

# Re-export SDK-independent utilities for backward compatibility.
# New code should import directly from sdk_adapter (the membrane).
from ._spec_utils import get_copilot_spec_origin

# =============================================================================
# SDK imports - THE ONLY PLACE IN THE CODEBASE where SDK is imported
# =============================================================================

# Only skip SDK imports if BOTH conditions are met:
# 1. SKIP_SDK_CHECK env var is set
# 2. pytest is actually running (convenience guard, NOT a security boundary)
_SKIP_SDK_CHECK = os.environ.get("SKIP_SDK_CHECK") and is_pytest_running()

# Guard against import failures - fail fast with clear error
# Unless SKIP_SDK_CHECK is set (for testing without SDK)
CopilotClient: Any
PermissionRequestResult: Any
SubprocessConfig: Any

if _SKIP_SDK_CHECK:
    # Test mode: provide None stubs that tests can mock
    CopilotClient = None  # type: ignore[misc,assignment]
    PermissionRequestResult = None  # type: ignore[misc,assignment]
    SubprocessConfig = None  # type: ignore[misc,assignment]
else:
    try:
        from copilot import CopilotClient  # type: ignore[import-untyped,no-redef]
    except ImportError as e:
        raise ImportError(
            "github-copilot-sdk not installed. Install with: pip install github-copilot-sdk"
        ) from e

    # SDK v0.3.0: SubprocessConfig is at copilot root (re-exported from copilot.client).
    from copilot import SubprocessConfig  # type: ignore[import-untyped,no-redef]

    # SDK v0.3.0: PermissionRequestResult is at copilot.session (canonical since v0.2.1).
    from copilot.session import (  # type: ignore[import-untyped]
        PermissionRequestResult,  # type: ignore[no-redef]
    )

# =============================================================================
# Exports
# =============================================================================


def make_permission_denied() -> Any:
    """Construct a PermissionRequestResult that rejects the permission request.

    Encapsulates ALL SDK field knowledge so client.py expresses intent only.

    SDK v0.3.0 API: PermissionRequestResult(kind=...) — single field.
    SDK v0.3.0 valid kinds: 'approve-once' | 'reject' | 'user-not-available' | 'no-result'

    Test mode (SKIP_SDK_CHECK=1): PermissionRequestResult is None; returns dict.
    """
    if PermissionRequestResult is not None:
        return PermissionRequestResult(kind="reject")  # type: ignore[return-value]  # pragma: no cover
    # Test mode only (SKIP_SDK_CHECK=1 sets PermissionRequestResult = None).
    return {"kind": "reject"}


__all__ = [
    "CopilotClient",
    "PermissionRequestResult",
    "SubprocessConfig",
    "make_permission_denied",
    "get_copilot_spec_origin",  # Re-export from _spec_utils
]
