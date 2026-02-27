"""
SDK Contract + Display Tests.

This module validates our provider's assumptions about the Copilot SDK's data structures
and ensures display-related bugs (like "unknown" tool names) don't regress.

WHY THIS EXISTS (Bug #19 Lessons):
- Test mocks matched our code assumptions, not actual SDK behavior
- Display path wasn't tested - "unknown" appeared in console but tests passed
- No SDK schema validation - we assumed OpenAI field names

These tests prevent:
1. Field name drift when SDK updates
2. Display bugs where valid data shows as "unknown"
3. Model name format confusion (dash vs dot)

Evidence: session 94f00edf (2026-02-19) — tool names showed "unknown"
"""

from __future__ import annotations

import errno

import pytest

from amplifier_module_provider_github_copilot.model_cache import (
    BUNDLED_MODEL_LIMITS,
    _normalize_model_name,
    get_fallback_limits,
)
from amplifier_module_provider_github_copilot.client import (
    _is_subprocess_dead_error,
)


# =============================================================================
# Model Name Normalization Tests
# =============================================================================


class TestModelNameNormalization:
    """Tests for _normalize_model_name() helper."""

    def test_dash_to_dot_conversion(self):
        """claude-opus-4-5 should normalize to claude-opus-4.5."""
        assert _normalize_model_name("claude-opus-4-5") == "claude-opus-4.5"

    def test_already_dot_format(self):
        """claude-opus-4.5 should remain unchanged."""
        assert _normalize_model_name("claude-opus-4.5") == "claude-opus-4.5"

    def test_normalize_gpt_versions(self):
        """gpt-5-1 should normalize to gpt-5.1."""
        assert _normalize_model_name("gpt-5-1") == "gpt-5.1"

    def test_no_version_suffix(self):
        """Model without version suffix should remain unchanged."""
        assert _normalize_model_name("claude-opus") == "claude-opus"

    def test_single_digit_suffix(self):
        """Model with single digit (not pair) should remain unchanged."""
        assert _normalize_model_name("gpt-5") == "gpt-5"

    def test_middle_dashes_preserved(self):
        """Dashes in the middle of model name should be preserved."""
        # Only the version pair at END is converted
        assert _normalize_model_name("claude-opus-fast-4-5") == "claude-opus-fast-4.5"

    def test_triple_version_not_affected(self):
        """Only last two digits are converted: -1-2-3 → -1-2.3."""
        assert _normalize_model_name("model-1-2-3") == "model-1-2.3"


class TestGetFallbackLimitsNormalization:
    """Tests that get_fallback_limits uses normalization."""

    def test_exact_match(self):
        """Exact model name should return limits."""
        result = get_fallback_limits("claude-opus-4.5")
        assert result is not None
        assert result == (200000, 32000)

    def test_normalized_match(self):
        """Dash-format model name should normalize and match."""
        result = get_fallback_limits("claude-opus-4-5")
        assert result is not None
        assert result == (200000, 32000)

    def test_unknown_model(self):
        """Unknown model should return None."""
        result = get_fallback_limits("unknown-model-9-9")
        assert result is None

    def test_all_bundled_models_accessible(self):
        """All bundled models should be accessible via get_fallback_limits."""
        for model_id in BUNDLED_MODEL_LIMITS:
            result = get_fallback_limits(model_id)
            assert result is not None, f"Model {model_id} not accessible"
            assert len(result) == 2, f"Model {model_id} has wrong format"


# =============================================================================
# Subprocess Dead Error Detection Tests
# =============================================================================


class TestSubprocessDeadErrorDetection:
    """Tests for _is_subprocess_dead_error() helper."""

    def test_broken_pipe_error_instance(self):
        """BrokenPipeError should be detected."""
        assert _is_subprocess_dead_error(BrokenPipeError())

    def test_connection_reset_error_instance(self):
        """ConnectionResetError should be detected."""
        assert _is_subprocess_dead_error(ConnectionResetError())

    def test_oserror_epipe(self):
        """OSError with EPIPE (errno 32) should be detected."""
        error = OSError(errno.EPIPE, "Broken pipe")
        assert _is_subprocess_dead_error(error)

    def test_oserror_econnreset(self):
        """OSError with ECONNRESET (errno 104) should be detected."""
        error = OSError(errno.ECONNRESET, "Connection reset by peer")
        assert _is_subprocess_dead_error(error)

    def test_unrelated_error_not_detected(self):
        """Unrelated errors should not be detected."""
        error = ValueError("Invalid argument")
        assert not _is_subprocess_dead_error(error)

    def test_timeout_error_not_detected(self):
        """TimeoutError should not be detected as subprocess dead."""
        assert not _is_subprocess_dead_error(TimeoutError())

    def test_oserror_other_errno_not_detected(self):
        """OSError with other errno should not be detected."""
        error = OSError(errno.ENOENT, "No such file")
        assert not _is_subprocess_dead_error(error)


# =============================================================================
# CopilotModelInfo Field Validation Tests
# =============================================================================


class TestCopilotModelInfoContract:
    """Tests that CopilotModelInfo has expected fields."""

    def test_required_fields_exist(self):
        """CopilotModelInfo should have all required fields."""
        from amplifier_module_provider_github_copilot.models import CopilotModelInfo
        import dataclasses

        fields = {f.name for f in dataclasses.fields(CopilotModelInfo)}
        required = {
            "id",
            "name",
            "provider",
            "context_window",
            "max_output_tokens",
            "supports_tools",
            "supports_vision",
            "supports_extended_thinking",
        }
        assert required.issubset(fields), f"Missing fields: {required - fields}"

    def test_field_types(self):
        """CopilotModelInfo fields should have correct types."""
        from amplifier_module_provider_github_copilot.models import CopilotModelInfo

        info = CopilotModelInfo(
            id="test-model",
            name="Test Model",
            provider="test",
            context_window=128000,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=False,
            supports_extended_thinking=False,
        )
        assert isinstance(info.id, str)
        assert isinstance(info.name, str)
        assert isinstance(info.context_window, int)
        assert isinstance(info.max_output_tokens, int)
        assert isinstance(info.supports_tools, bool)


# =============================================================================
# Tool Name Display Tests (Bug #19 Prevention)
# =============================================================================


class TestToolNameDisplay:
    """Tests that tool names are correctly extracted and never show 'unknown'."""

    def test_tool_field_extraction(self):
        """Tool name should be extracted from 'tool' field (Amplifier format)."""
        from amplifier_module_provider_github_copilot.converters import (
            convert_messages_to_prompt,
        )

        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "tool": "read_file",  # Amplifier transcript format
                        "arguments": {"path": "/test.txt"},
                    }
                ],
            }
        ]
        result = convert_messages_to_prompt(messages)
        assert "read_file" in result
        assert "unknown" not in result.lower()

    def test_name_field_fallback(self):
        """Tool name should fall back to 'name' field (SDK format)."""
        from amplifier_module_provider_github_copilot.converters import (
            convert_messages_to_prompt,
        )

        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "name": "edit_file",  # SDK format
                        "arguments": {"path": "/test.txt"},
                    }
                ],
            }
        ]
        result = convert_messages_to_prompt(messages)
        assert "edit_file" in result
        assert "unknown" not in result.lower()

    def test_function_field_fallback(self):
        """Tool name should fall back to function.name (OpenAI format)."""
        from amplifier_module_provider_github_copilot.converters import (
            convert_messages_to_prompt,
        )

        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "function": {"name": "create_file", "arguments": "{}"},
                    }
                ],
            }
        ]
        result = convert_messages_to_prompt(messages)
        assert "create_file" in result
        assert "unknown" not in result.lower()

    def test_all_fields_missing_shows_unknown(self):
        """Only when ALL fields are missing should 'unknown' appear."""
        from amplifier_module_provider_github_copilot.converters import (
            convert_messages_to_prompt,
        )

        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        # No tool, name, or function field
                        "arguments": {},
                    }
                ],
            }
        ]
        result = convert_messages_to_prompt(messages)
        # This is the ONLY valid case where unknown should appear
        assert "unknown" in result.lower()
