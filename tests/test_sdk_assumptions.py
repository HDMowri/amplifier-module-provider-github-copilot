"""Tier 6: SDK Assumption Tests - verify SDK types and shapes without API calls.

These tests import the real SDK, instantiate objects, and verify our structural
assumptions. They require the SDK to be installed but do NOT make API calls.

Contract references:
- contracts/sdk-boundary.md
- contracts/deny-destroy.md

Run: pytest -m sdk_assumption -v
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest


@pytest.mark.sdk_assumption
class TestSDKImportAssumptions:
    """Verify SDK module structure matches our assumptions.

    AC-1: SDK Import Assumptions
    """

    def test_copilot_client_class_exists(self, sdk_module: Any) -> None:
        """We assume copilot.CopilotClient exists and is importable.

        # Contract: sdk-boundary:Lifecycle:MUST:1
        """
        assert isinstance(sdk_module.CopilotClient, type)

    def test_client_has_create_session(self, sdk_module: Any) -> None:
        """We assume CopilotClient has create_session method.

        # Contract: sdk-boundary:Session:MUST:1
        """
        assert inspect.iscoroutinefunction(sdk_module.CopilotClient.create_session)

    def test_client_has_start_stop(self, sdk_module: Any) -> None:
        """We assume CopilotClient has start() and stop() lifecycle methods.

        # Contract: sdk-boundary:Lifecycle:MUST:1
        """
        assert inspect.iscoroutinefunction(sdk_module.CopilotClient.start)
        assert inspect.iscoroutinefunction(sdk_module.CopilotClient.stop)

    def test_subprocess_config_importable(self, sdk_module: Any) -> None:
        """SubprocessConfig must be importable from copilot root (canonical path since v0.2.1).

        # Contract: sdk-boundary:Auth:MUST:1

        copilot.types was deleted in SDK v0.2.1. SubprocessConfig now lives at copilot root.
        Verifies _imports.py's direct import path is correct.
        """
        from copilot import SubprocessConfig  # type: ignore[import-untyped]

        assert isinstance(SubprocessConfig, type), (
            "SubprocessConfig must be a class importable from copilot"
        )
        # Instantiate and verify a known field
        instance = SubprocessConfig(github_token="test-token")
        assert instance.github_token == "test-token"


@pytest.mark.sdk_assumption
class TestPermissionRequestResultV030Schema:
    """SDK v0.3.0 introduced a breaking change to PermissionRequestResult.

    Previously (v0.2.x) the result carried multiple fields (kind, rules, feedback,
    message, path) and used kind values 'denied-by-rules' / 'approved'. The v0.3.0
    release reduced the result to kind-only, removed rules/feedback/message/path,
    and renamed the kind values to 'reject' / 'approve-once'.

    These tests pin the v0.3.0 schema we ship against, so any future SDK version
    that mutates this surface (additional fields, renamed kinds, removed kinds)
    fails LOUDLY before reaching production.

    Contract: sdk-boundary:ImportQuarantine:MUST:7
    """

    def test_kind_literal_contains_exactly_v030_values(self, sdk_module: Any) -> None:
        """PermissionRequestResultKind Literal MUST equal exactly the v0.3.0 set.

        If the SDK adds, removes, or renames a kind value, our factory and
        deny-destroy flow may silently break. Pin the set explicitly.

        Contract: sdk-boundary:ImportQuarantine:MUST:7
        """
        from typing import get_args

        from copilot.session import PermissionRequestResultKind  # type: ignore[import-untyped]

        observed = set(get_args(PermissionRequestResultKind))
        expected = {"approve-once", "reject", "user-not-available", "no-result"}
        assert observed == expected, (
            f"SDK PermissionRequestResultKind drifted from v0.3.0 contract.\n"
            f"  Expected: {sorted(expected)}\n"
            f"  Observed: {sorted(observed)}\n"
            f"  Added: {sorted(observed - expected)}\n"
            f"  Removed: {sorted(expected - observed)}\n"
            f"Update _imports.make_permission_denied() and rerun the SDK diff workflow."
        )

    def test_factory_produces_sdk_accepted_reject_result(self, sdk_module: Any) -> None:
        """make_permission_denied() MUST construct a real SDK object with kind='reject'.

        End-to-end check: the factory's output is assignable to a real SDK
        PermissionRequestResult and carries the v0.3.0 'reject' kind. Also
        verifies the result has NO legacy v0.2.x fields (rules/feedback/message/path)
        since the SDK contract now forbids them.

        SKIP_SDK_CHECK is cleared and _imports is reloaded so the factory exercises
        the real SDK code path (conftest.py sets SKIP_SDK_CHECK=1 by default to keep
        the rest of the suite SDK-binary-free).

        Contract: sdk-boundary:ImportQuarantine:MUST:7
        Contract: deny-destroy:PermissionRequest:MUST:2
        """
        import importlib
        import os

        from copilot.session import PermissionRequestResult  # type: ignore[import-untyped]

        from amplifier_module_provider_github_copilot.sdk_adapter import _imports

        # Force the real SDK code path even though conftest set SKIP_SDK_CHECK=1
        original = os.environ.pop("SKIP_SDK_CHECK", None)
        try:
            importlib.reload(_imports)
            result = _imports.make_permission_denied()
        finally:
            if original is not None:
                os.environ["SKIP_SDK_CHECK"] = original
            importlib.reload(_imports)

        # Real SDK type, not the dict fallback (which is test-mode only)
        assert isinstance(result, PermissionRequestResult), (
            f"Factory returned {type(result).__name__}, expected PermissionRequestResult. "
            "Dict fallback should only occur in test mode (SKIP_SDK_CHECK=1)."
        )
        # Exact v0.3.0 kind
        assert result.kind == "reject", (
            f"Factory returned kind={result.kind!r}, expected 'reject'. "
            "v0.2.x used 'denied-by-rules' — never reintroduce."
        )
        # v0.2.x legacy fields must not exist on the v0.3.0 result
        for forbidden in ("rules", "feedback", "message", "path"):
            assert not hasattr(result, forbidden), (
                f"PermissionRequestResult exposes legacy v0.2.x field '{forbidden}'. "
                "v0.3.0 reduced the surface to kind-only — SDK regressed."
            )
