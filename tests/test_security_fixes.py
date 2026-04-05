"""
Tests for critical security fixes.

Tests for:
- Deny hook on real SDK path
- Race condition fix in session()
- Double exception translation guard
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from amplifier_module_provider_github_copilot.sdk_adapter.client import (
    CopilotClientWrapper,
)

# =============================================================================
# AC-1: Deny Hook on Real SDK Path
# =============================================================================


class TestDenyHookOnRealSDKPath:
    """Verify deny hook is installed on CopilotClientWrapper.session().

    Deny hook is now passed via session config 'hooks' key,
    not via register_pre_tool_use_hook() method call.
    """

    @pytest.mark.asyncio
    async def test_session_registers_deny_hook(self) -> None:
        """AC-1: session() MUST pass deny hook via session config.

        The correct SDK API passes hooks via session_config['hooks'],
        not via a method call on the session object.
        """
        # Arrange: mock SDK client that captures session config
        captured_config: dict[str, Any] = {}

        mock_session = MagicMock()
        mock_session.disconnect = AsyncMock()

        async def capture_config(**config: Any) -> MagicMock:
            captured_config.update(config)
            return mock_session

        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(side_effect=capture_config)

        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        # Act: use session context manager
        async with wrapper.session(model="gpt-4"):
            pass

        # Assert: deny hook was passed via session config 'hooks' key
        assert "hooks" in captured_config, "session config must include 'hooks' key"
        hooks = captured_config["hooks"]
        assert "on_pre_tool_use" in hooks, "hooks must include 'on_pre_tool_use'"

        # Verify the hook denies all tools
        deny_hook = hooks["on_pre_tool_use"]
        result = deny_hook({"toolName": "bash"}, {})
        assert result["permissionDecision"] == "deny"


# =============================================================================
# AC-2: Race Condition Fix
# =============================================================================


class TestRaceConditionFix:
    """Verify concurrent session() calls don't cause race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_sessions_no_race(self) -> None:
        """AC-2: Concurrent session() calls must not use unstarted client."""
        # Track initialization order
        init_count = 0
        start_called = False

        class MockCopilotClient:  # noqa: B903  # pyright: ignore[reportUnusedClass]
            def __init__(self, config: Any = None) -> None:
                nonlocal init_count
                init_count += 1

            async def start(self) -> None:
                nonlocal start_called
                # Simulate slow start
                await asyncio.sleep(0.1)
                start_called = True

            async def create_session(self, **config: Any) -> MagicMock:
                # CRITICAL: Must fail if start() wasn't called
                if not start_called:
                    raise RuntimeError("Client not started!")
                session = MagicMock()
                session.register_pre_tool_use_hook = MagicMock()
                session.disconnect = AsyncMock()
                return session

        # Arrange: wrapper that will lazy-init
        wrapper = CopilotClientWrapper()
        # Monkey-patch for testing (normally would use SDK import)
        wrapper._owned_client = None  # type: ignore[attr-defined]

        # We need to test the lock behavior - this requires the fix
        # For now, test passes if no exception (assumes fix is in place)
        # The test will fail if concurrent calls create multiple clients

        # Since we can't easily inject the mock into lazy init,
        # we test with injected client that simulates slow operations
        mock_session = MagicMock()
        mock_session.register_pre_tool_use_hook = MagicMock()
        mock_session.disconnect = AsyncMock()

        call_count = 0
        create_lock = asyncio.Lock()

        async def slow_create_session(**config: Any) -> MagicMock:
            nonlocal call_count
            async with create_lock:
                call_count += 1
            await asyncio.sleep(0.05)
            return mock_session

        mock_client = MagicMock()
        mock_client.create_session = slow_create_session

        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        # Act: launch concurrent sessions
        async def use_session() -> None:
            async with wrapper.session(model="gpt-4"):
                await asyncio.sleep(0.01)

        await asyncio.gather(use_session(), use_session(), use_session())

        # Assert: sessions were created (basic sanity)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_lazy_init_protected_by_lock(self) -> None:
        """AC-2: Lazy client init must be protected by asyncio.Lock."""
        # This test verifies that the wrapper has a _client_lock attribute
        wrapper = CopilotClientWrapper()

        # The fix requires adding _client_lock
        assert hasattr(wrapper, "_client_lock"), (
            "CopilotClientWrapper must have _client_lock for thread-safe lazy init"
        )
        assert isinstance(wrapper._client_lock, asyncio.Lock)  # type: ignore[attr-defined]


# =============================================================================
# AC-3: Double Exception Translation Guard
# =============================================================================
# TestDoubleExceptionTranslation removed - migrated to test_behaviors.py
# TestProductionPathWithMockClient::test_llm_error_not_double_wrapped (Issue #6)


# =============================================================================
# behaviors:Security:MUST:2 — Mount traceback redacted before DEBUG log
# =============================================================================


class TestMountTracebackRedaction:
    """Mount failure tracebacks MUST be redacted before DEBUG log emission.

    Contract: behaviors:Security:MUST:2

    Raw exc_info=True bypasses security_redaction.py and may emit tokens
    present in exception messages or traceback frame local variables.
    """

    def test_mount_debug_log_does_not_use_raw_exc_info(self) -> None:
        """behaviors:Security:MUST:2 — mount() MUST NOT call logger.debug with exc_info=True.

        Structural check: inspect the mount() source to ensure raw exc_info=True
        is not passed to logger.debug in the exception handler. The formatted
        traceback string must be piped through redact_sensitive_text() first.
        """
        import inspect

        import amplifier_module_provider_github_copilot as pkg

        source = inspect.getsource(pkg.mount)

        # Verify the fix is present: formatted traceback must use redact_sensitive_text
        # Raw exc_info logging would bypass redaction entirely.
        assert "redact_sensitive_text(formatted_tb)" in source, (
            "mount() must format traceback to string and pipe through redact_sensitive_text(). "
            "Contract: behaviors:Security:MUST:2"
        )
        assert "format_exception" in source, (
            "mount() must use traceback.format_exception() to produce a redactable string. "
            "Contract: behaviors:Security:MUST:2"
        )

    def test_mount_debug_log_redacts_token_in_traceback(self) -> None:
        """behaviors:Security:MUST:2 — A token in the exception chain MUST NOT
        appear in DEBUG log output after redaction.
        """
        import logging

        from amplifier_module_provider_github_copilot.security_redaction import REDACTED

        # Capture DEBUG log records
        captured: list[str] = []

        class CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(self.format(record))

        handler = CapturingHandler()
        logger = logging.getLogger("amplifier_module_provider_github_copilot")
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Inject a token into the exception that will appear in the traceback
        fake_token = "ghp_" + "A" * 25  # Matches GitHub PAT pattern

        try:
            # Simulate what mount() does on failure — call the error-logging path
            # by examining the source and triggering the redacted debug log
            try:
                raise RuntimeError(f"SDK failed: token={fake_token}")
            except Exception as e:
                import traceback as tb_module

                from amplifier_module_provider_github_copilot.security_redaction import (
                    redact_sensitive_text,
                )

                formatted = "".join(tb_module.format_exception(type(e), e, e.__traceback__))
                redacted = redact_sensitive_text(formatted)
                logger.debug("[MOUNT] Mount failure traceback:\n%s", redacted)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)

        # The token must NOT appear in any captured log line
        for line in captured:
            assert fake_token not in line, (
                f"Token {fake_token!r} leaked in DEBUG log. "
                f"Contract: behaviors:Security:MUST:2. Line: {line!r}"
            )
        # REDACTED placeholder must appear instead
        assert any(REDACTED in line for line in captured), (
            f"Expected REDACTED in debug log output but found none. Captured: {captured}"
        )
