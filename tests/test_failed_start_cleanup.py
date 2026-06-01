"""Tests for SDK client failed-start cleanup.

Contract: contracts/sdk-boundary.md — client lifecycle must be resilient to start failures

Tests verify:
- Failed start() clears _owned_client to None
- Next session attempt re-initializes the client
- Original exception is still propagated
- Retry after failure succeeds

Note: These tests pin the b10 CopilotClient keyword-argument constructor.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _MockSDKSession:
    """Minimal stub for the raw SDK session object used in cleanup tests."""

    session_id: str = "test-session"

    async def disconnect(self) -> None: ...


class _MockSDKClient:
    """Minimal stub for copilot.CopilotClient used in cleanup tests."""

    async def create_session(self, **kwargs: Any) -> _MockSDKSession: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class TestFailedStartCleanup:
    """SDK Client Failed-Start Cleanup.

    # Contract: sdk-boundary:client-lifecycle:MUST:1
    """

    @pytest.mark.asyncio
    async def test_failed_start_clears_owned_client(self) -> None:
        """sdk-boundary:client-lifecycle:MUST:1 — failed start must clear _owned_client.

        When start() raises an exception, _owned_client MUST be reset to None
        so subsequent session() calls can retry initialization.
        """
        from amplifier_module_provider_github_copilot.error_translation import (
            ProviderUnavailableError,
        )
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()

        # Mock CopilotClient to raise on start()
        mock_client_instance = MagicMock(spec=_MockSDKClient)
        mock_client_instance.start = AsyncMock(side_effect=RuntimeError("Start failed"))

        def construct_client(
            *,
            base_directory: str,
            github_token: str | None = None,
            log_level: str = "info",
            env: dict[str, str],
            mode: str = "copilot-cli",
        ) -> MagicMock:
            return mock_client_instance

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
            # Patch where CopilotClient is used
            with (
                patch(
                    "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
                    construct_client,
                ),
            ):
                # RuntimeError from start() is translated to ProviderUnavailableError
                with pytest.raises(ProviderUnavailableError):
                    async with wrapper.session(model="gpt-4"):
                        pass

                # CRITICAL: _owned_client should be None after failed start
                # This is the bug fix — previously it retained the broken client
                assert wrapper._owned_client is None  # type: ignore[reportPrivateUsage]  # Testing internal state

    @pytest.mark.asyncio
    async def test_retry_after_failed_start_reinitializes_client(self) -> None:
        """Contract: sdk-boundary:client-lifecycle:MUST:2 — retry after failure must reinitialize.

        After a failed start(), the next session() call MUST attempt
        to create a new CopilotClient instance.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()

        call_count = 0

        def create_client(
            *,
            base_directory: str,
            github_token: str | None = None,
            log_level: str = "info",
            env: dict[str, str],
            mode: str = "copilot-cli",
        ) -> MagicMock:
            nonlocal call_count
            call_count += 1
            mock_client = MagicMock(spec=_MockSDKClient)
            if call_count == 1:
                # First call: start fails
                mock_client.start = AsyncMock(side_effect=RuntimeError("Start failed"))
            else:
                # Second call: start succeeds
                mock_client.start = AsyncMock()
                mock_session = MagicMock(spec=_MockSDKSession)
                mock_session.disconnect = AsyncMock()
                # Use on() + send() pattern instead of register_pre_tool_use_hook
                mock_session.on = MagicMock(return_value=lambda: None)
                mock_session.send = AsyncMock(return_value="message-id")
                mock_client.create_session = AsyncMock(return_value=mock_session)
            return mock_client

        mock_client_class = MagicMock(side_effect=create_client)

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
            # Patch where CopilotClient is used
            with (
                patch(
                    "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
                    mock_client_class,
                ),
            ):
                # First attempt: should fail
                # RuntimeError from start() is translated to ProviderUnavailableError
                from amplifier_module_provider_github_copilot.error_translation import (
                    ProviderUnavailableError,
                )

                with pytest.raises(ProviderUnavailableError):
                    async with wrapper.session(model="gpt-4"):
                        pass

                # Second attempt: should succeed (new client created)
                async with wrapper.session(model="gpt-4"):
                    pass

                # Verify client was created twice (not reused from first failed attempt)
                assert call_count == 2

    @pytest.mark.asyncio
    async def test_original_exception_propagated(self) -> None:
        """Contract: sdk-boundary:client-lifecycle:MUST:3 — original exception must be propagated.

        When start() raises, the exception (or translated version) must propagate
        to the caller. The cleanup must not swallow the error.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()

        mock_client_instance = MagicMock(spec=_MockSDKClient)
        mock_client_instance.start = AsyncMock(side_effect=RuntimeError("Connection refused"))

        def construct_client(
            *,
            base_directory: str,
            github_token: str | None = None,
            log_level: str = "info",
            env: dict[str, str],
            mode: str = "copilot-cli",
        ) -> MagicMock:
            return mock_client_instance

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
            # Patch where CopilotClient is used
            with (
                patch(
                    "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
                    construct_client,
                ),
            ):
                # RuntimeError from start() is translated to ProviderUnavailableError
                from amplifier_module_provider_github_copilot.error_translation import (
                    ProviderUnavailableError,
                )

                with pytest.raises(ProviderUnavailableError) as exc_info:
                    async with wrapper.session(model="gpt-4"):
                        pass

                # Exception should be raised with original context (not swallowed)
                assert isinstance(exc_info.value, ProviderUnavailableError)
                assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_successful_start_retains_client(self) -> None:
        """sdk-boundary:client-lifecycle:REGRESSION — successful start must retain client.

        When start() succeeds, _owned_client MUST be retained for reuse
        in subsequent session() calls. This is regression coverage.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()

        mock_client_instance = MagicMock(spec=_MockSDKClient)
        mock_client_instance.start = AsyncMock()
        mock_session = MagicMock(spec=_MockSDKSession)
        mock_session.disconnect = AsyncMock()
        # Use on() + send() pattern instead of register_pre_tool_use_hook
        mock_session.on = MagicMock(return_value=lambda: None)
        mock_session.send = AsyncMock(return_value="message-id")
        mock_client_instance.create_session = AsyncMock(return_value=mock_session)

        construct_count = 0

        def construct_client(
            *,
            base_directory: str,
            github_token: str | None = None,
            log_level: str = "info",
            env: dict[str, str],
            mode: str = "copilot-cli",
        ) -> MagicMock:
            nonlocal construct_count
            construct_count += 1
            return mock_client_instance

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
            # Patch where CopilotClient is used
            with (
                patch(
                    "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
                    construct_client,
                ),
            ):
                async with wrapper.session(model="gpt-4"):
                    pass

                # After successful start, _owned_client should be retained
                assert wrapper._owned_client is mock_client_instance  # type: ignore[reportPrivateUsage]  # Testing internal state

                # Second session should reuse the same client
                async with wrapper.session(model="gpt-4"):
                    pass

                # CopilotClient constructor must be called exactly once across
                # both sessions — the start.call_count assertion alone would
                # silently pass if a future refactor returned a fresh mock per
                # construct call (only the original mock's start would stay 1).
                assert construct_count == 1, (
                    "CopilotClient constructor must be called exactly once across both sessions"
                )
                assert mock_client_instance.start.call_count == 1
