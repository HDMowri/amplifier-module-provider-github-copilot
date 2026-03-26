"""Tests for event classification overlap validation.

Contract: contracts/event-vocabulary.md -- event classification must be unambiguous.

The problem: If the same event type appears in both bridge mappings and consume/drop
patterns, BRIDGE wins silently. This is a config error that should be detected at load time.
"""

from pathlib import Path

import pytest

from amplifier_module_provider_github_copilot.streaming import load_event_config


class TestEventClassificationOverlapValidation:
    """Validate no overlap between BRIDGE, CONSUME, and DROP categories."""

    def test_overlapping_bridge_and_consume_raises_error(self, tmp_path: Path) -> None:
        """Overlap between bridge and consume must raise ConfigurationError.

        Contract: event-vocabulary:Classification:MUST:1 -- each event type has exactly one
        classification.
        """
        config_yaml = tmp_path / "events.yaml"
        config_yaml.write_text(
            """
event_classifications:
  bridge:
    - sdk_type: assistant.message_delta
      domain_type: CONTENT_DELTA
      block_type: TEXT
  consume:
    - assistant.message_delta  # OVERLAP -- same as bridge entry
  drop: []
"""
        )

        with pytest.raises(Exception) as exc_info:
            load_event_config(config_yaml)

        # Should be ConfigurationError with details about the conflict
        assert "overlap" in str(exc_info.value).lower() or "assistant.message_delta" in str(
            exc_info.value
        )

    def test_overlapping_bridge_and_drop_raises_error(self, tmp_path: Path) -> None:
        """Overlap between bridge and drop must raise ConfigurationError.

        Contract: event-vocabulary:Classification:MUST:1
        """
        config_yaml = tmp_path / "events.yaml"
        config_yaml.write_text(
            """
event_classifications:
  bridge:
    - sdk_type: error
      domain_type: ERROR
  consume: []
  drop:
    - error  # OVERLAP -- same as bridge entry
"""
        )

        with pytest.raises(Exception) as exc_info:
            load_event_config(config_yaml)

        assert "overlap" in str(exc_info.value).lower() or "error" in str(exc_info.value)

    def test_overlapping_consume_and_drop_raises_error(self, tmp_path: Path) -> None:
        """Overlap between consume and drop must raise ConfigurationError.

        Contract: event-vocabulary:Classification:MUST:1
        """
        config_yaml = tmp_path / "events.yaml"
        config_yaml.write_text(
            """
event_classifications:
  bridge: []
  consume:
    - session_created
  drop:
    - session_created  # OVERLAP -- same as consume entry
"""
        )

        with pytest.raises(Exception) as exc_info:
            load_event_config(config_yaml)

        assert "overlap" in str(exc_info.value).lower() or "session_created" in str(exc_info.value)

    def test_wildcard_overlap_detected(self, tmp_path: Path) -> None:
        """Wildcard patterns that overlap with bridge must be detected.

        Contract: event-vocabulary:Classification:MUST:1
        """
        config_yaml = tmp_path / "events.yaml"
        config_yaml.write_text(
            """
event_classifications:
  bridge:
    - sdk_type: tool_result_success
      domain_type: TOOL_CALL
  consume: []
  drop:
    - tool_result_*  # WILDCARD -- matches tool_result_success in bridge
"""
        )

        with pytest.raises(Exception) as exc_info:
            load_event_config(config_yaml)

        assert "overlap" in str(exc_info.value).lower() or "tool_result" in str(exc_info.value)

    def test_clean_config_loads_without_error(self, tmp_path: Path) -> None:
        """Clean config (no overlaps) loads successfully.

        Regression test to ensure validation doesn't break valid configs.
        """
        config_yaml = tmp_path / "events.yaml"
        config_yaml.write_text(
            """
event_classifications:
  bridge:
    - sdk_type: assistant.message_delta
      domain_type: CONTENT_DELTA
      block_type: TEXT
    - sdk_type: error
      domain_type: ERROR
  consume:
    - session_created
    - session_destroyed
  drop:
    - heartbeat
    - debug_*
"""
        )

        # Should NOT raise
        config = load_event_config(config_yaml)

        assert "assistant.message_delta" in config.bridge_mappings
        assert "session_created" in config.consume_patterns
        assert "heartbeat" in config.drop_patterns

    def test_production_config_loads_without_error(self) -> None:
        """Production config/events.yaml has no overlaps.

        Regression test for actual production config.
        """
        # Should NOT raise -- production config should be valid
        config = load_event_config()

        # Verify config loaded properly
        assert len(config.bridge_mappings) > 0
        assert len(config.consume_patterns) > 0
        assert len(config.drop_patterns) > 0

    def test_error_message_includes_conflicting_entry(self, tmp_path: Path) -> None:
        """Error message must include details about which entry conflicts.

        Contract: error-hierarchy:Context:SHOULD:1 -- errors include actionable context.
        """
        config_yaml = tmp_path / "events.yaml"
        config_yaml.write_text(
            """
event_classifications:
  bridge:
    - sdk_type: usage_update
      domain_type: USAGE_UPDATE
  consume:
    - usage_update
  drop: []
"""
        )

        with pytest.raises(Exception) as exc_info:
            load_event_config(config_yaml)

        error_msg = str(exc_info.value).lower()
        # Error should identify the conflicting event type
        assert "usage_update" in error_msg
        # And ideally which categories conflict
        assert "bridge" in error_msg or "consume" in error_msg


class TestEventPredicateExactMatching:
    """Verify event predicates use exact matching, not substring matching.

    Contract: event-vocabulary:Classification:MUST:1 — each event type has exactly one
    classification.

    Regression prevention: The predicates were using substring matching like
    `"idle" in type_lower` which would misclassify events like `session.idle_timeout`.
    """

    def test_is_idle_event_matches_session_idle(self) -> None:
        """is_idle_event MUST match session.idle."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_idle_event,
        )

        # These MUST match
        assert is_idle_event("session.idle") is True
        assert is_idle_event("SESSION_IDLE") is True  # Legacy/domain format
        assert is_idle_event("session_idle") is True  # Underscore variant

    def test_is_idle_event_does_not_match_substring_containing(self) -> None:
        """is_idle_event MUST NOT match events just because they contain 'idle'.

        Future SDK events like 'session.idle_timeout' should NOT trigger turn completion.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_idle_event,
        )

        # These MUST NOT match — they contain "idle" but are not idle events
        assert is_idle_event("session.idle_timeout") is False
        assert is_idle_event("session.idle_warning") is False
        assert is_idle_event("idle_check") is False

    def test_is_error_event_matches_session_error(self) -> None:
        """is_error_event MUST match session.error."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_error_event,
        )

        # These MUST match
        assert is_error_event("session.error") is True
        assert is_error_event("ERROR") is True  # Domain format
        assert is_error_event("error") is True  # Simple format

    def test_is_error_event_does_not_match_substring_containing(self) -> None:
        """is_error_event MUST NOT match events just because they contain 'error'.

        Recovery events like 'tool_error_recovered' should NOT terminate the stream.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_error_event,
        )

        # These MUST NOT match — they contain "error" but are not error events
        assert is_error_event("tool_error_recovered") is False
        assert is_error_event("error_recovery") is False
        assert is_error_event("error_cleared") is False
        assert is_error_event("session.error_handled") is False


class TestEventHelpersEdgeCases:
    """Tests for edge cases and None handling in event helpers.

    Contract: event-vocabulary:EdgeCases:MUST:1 — all helpers handle None safely.
    """

    def test_is_idle_event_returns_false_for_none(self) -> None:
        """is_idle_event MUST return False for None input."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_idle_event,
        )

        assert is_idle_event(None) is False

    def test_is_error_event_returns_false_for_none(self) -> None:
        """is_error_event MUST return False for None input."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_error_event,
        )

        assert is_error_event(None) is False

    def test_is_assistant_message_returns_false_for_none(self) -> None:
        """is_assistant_message MUST return False for None input."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_assistant_message,
        )

        assert is_assistant_message(None) is False

    def test_extract_event_type_returns_none_for_event_with_none_type(self) -> None:
        """extract_event_type MUST return None when event.type is None."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_event_type,
        )

        # Object with .type = None
        class MockEvent:
            type = None

        assert extract_event_type(MockEvent()) is None

    def test_extract_event_type_returns_none_for_dict_without_type(self) -> None:
        """extract_event_type MUST return None for dict without 'type' key."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_event_type,
        )

        assert extract_event_type({}) is None
        assert extract_event_type({"data": {}}) is None

    def test_extract_tool_requests_from_object_event_with_data(self) -> None:
        """extract_tool_requests handles object events with .data.tool_requests."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_tool_requests,
        )

        # Object event with data.tool_requests
        class MockData:
            tool_requests = [{"name": "tool1", "id": "123"}]

        class MockEvent:
            data = MockData()

        result = extract_tool_requests(MockEvent())
        assert len(result) == 1
        assert result[0]["name"] == "tool1"

    def test_extract_tool_requests_from_object_event_without_tool_requests(self) -> None:
        """extract_tool_requests returns empty list when no tool_requests."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_tool_requests,
        )

        # Object event with data but no tool_requests
        class MockData:
            pass

        class MockEvent:
            data = MockData()

        result = extract_tool_requests(MockEvent())
        assert result == []

    def test_extract_tool_requests_fallback_to_top_level(self) -> None:
        """extract_tool_requests checks top-level tool_requests as fallback."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_tool_requests,
        )

        # Event with tool_requests directly on event (no data attribute)
        class MockEvent:
            tool_requests = [{"name": "fallback_tool", "id": "456"}]

        result = extract_tool_requests(MockEvent())
        assert len(result) == 1
        assert result[0]["name"] == "fallback_tool"

    def test_extract_tool_requests_returns_empty_for_none_data(self) -> None:
        """extract_tool_requests returns empty list when data is None."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_tool_requests,
        )

        # Object event with data = None
        class MockEvent:
            data = None

        result = extract_tool_requests(MockEvent())
        assert result == []

    def test_has_tool_capture_event_returns_false_for_non_assistant_message(self) -> None:
        """has_tool_capture_event requires ASSISTANT_MESSAGE event type."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            has_tool_capture_event,
        )

        # Event that is NOT assistant.message
        event = {"type": "session.idle", "data": {"tool_requests": [{"name": "foo"}]}}
        assert has_tool_capture_event(event) is False

    def test_has_tool_capture_event_returns_true_for_assistant_message_with_tools(
        self,
    ) -> None:
        """has_tool_capture_event returns True for assistant.message with tool_requests."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            has_tool_capture_event,
        )

        event = {
            "type": "assistant.message",
            "data": {"tool_requests": [{"name": "run_command"}]},
        }
        assert has_tool_capture_event(event) is True

    def test_is_assistant_message_matches_variations(self) -> None:
        """is_assistant_message matches various formats."""
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_assistant_message,
        )

        # Should match
        assert is_assistant_message("assistant.message") is True
        assert is_assistant_message("ASSISTANT_MESSAGE") is True
        assert is_assistant_message("assistant_message") is True

        # Should NOT match (delta events)
        assert is_assistant_message("assistant.message_delta") is False
        assert is_assistant_message("ASSISTANT_MESSAGE_DELTA") is False
