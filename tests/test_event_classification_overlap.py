"""Tests for event classification overlap validation.

Contract: contracts/event-vocabulary.md -- event classification must be unambiguous.

The problem: If the same event type appears in both bridge mappings and consume/drop
patterns, BRIDGE wins silently. This is a config error that should be detected at load time.
"""

from pathlib import Path

import pytest

from amplifier_module_provider_github_copilot._compat import ConfigurationError
from amplifier_module_provider_github_copilot.streaming import (
    DomainEventType,
    _validate_no_classification_overlap,  # pyright: ignore[reportPrivateUsage]
    load_event_config,
)


class TestEventClassificationOverlapValidation:
    """Validate production event config has no overlaps.

    Contract: event-vocabulary:Classification:MUST:1
    """

    def test_production_config_loads_without_error(self) -> None:
        """Production config has no overlaps.

        # Contract: event-vocabulary:Classification:MUST:1
        Regression test for actual production config.
        """
        # Should NOT raise -- production config should be valid
        config = load_event_config()

        # Verify config loaded properly
        assert len(config.bridge_mappings) > 0
        assert len(config.consume_patterns) > 0
        assert len(config.drop_patterns) > 0


class TestEventPredicateExactMatching:
    """Verify event predicates use exact matching, not substring matching.

    Contract: event-vocabulary:Classification:MUST:1 — each event type has exactly one
    classification.

    Regression prevention: The predicates were using substring matching like
    `"idle" in type_lower` which would misclassify events like `session.idle_timeout`.
    """

    def test_is_idle_event_matches_session_idle(self) -> None:
        """is_idle_event MUST match session.idle.

        # Contract: event-vocabulary:Classification:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_idle_event,
        )

        # These MUST match
        assert is_idle_event("session.idle") is True
        assert is_idle_event("SESSION_IDLE") is True  # Legacy/domain format
        assert is_idle_event("session_idle") is True  # Underscore variant

    def test_is_idle_event_does_not_match_substring_containing(self) -> None:
        """is_idle_event MUST NOT match events just because they contain 'idle'.

        # Contract: event-vocabulary:Classification:MUST:1
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
        """is_error_event MUST match session.error.

        # Contract: event-vocabulary:Classification:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_error_event,
        )

        # These MUST match
        assert is_error_event("session.error") is True
        assert is_error_event("ERROR") is True  # Domain format
        assert is_error_event("error") is True  # Simple format

    def test_is_error_event_does_not_match_substring_containing(self) -> None:
        """is_error_event MUST NOT match events just because they contain 'error'.

        # Contract: event-vocabulary:Classification:MUST:1
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


class TestEmptySetFallback:
    """Tests for empty set fallback behavior in event helpers.

    DEFENSIVE SAFETY NET - NOT PRIMARY BEHAVIOR.

    Primary behavior: load_event_config() raises ConfigurationError if
    session_lifecycle.idle_events is empty (fail-fast at load time).

    These fallbacks exist for defense in depth:
    - If config validation is somehow bypassed
    - If tests call helpers directly without config
    - Historical edge cases

    Bug discovered: Session hung forever because is_idle_event(evt, idle_events=set())
    used `if idle_events is not None` which is True for empty set, causing it to check
    `type_lower in set()` which is always False => idle never detected => infinite hang.

    Fix: Changed to `if idle_events:` which is False for empty set, triggering fallback.
    Prevention: Added fail-fast validation in load_event_config() at load time.
    """

    def test_is_idle_event_empty_set_uses_fallback(self) -> None:
        """is_idle_event MUST use fallback when empty set is passed.

        # Contract: streaming-contract:SessionLifecycle:MUST:1
        Critical regression test: If EventConfig has empty idle_event_types,
        the helper must fall back to hardcoded defaults, not hang forever.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_idle_event,
        )

        # Empty set MUST fall back to hardcoded defaults
        assert is_idle_event("session.idle", idle_events=set()) is True
        assert is_idle_event("idle", idle_events=set()) is True
        assert is_idle_event("session_idle", idle_events=set()) is True

    def test_is_error_event_empty_set_uses_fallback(self) -> None:
        """is_error_event MUST use fallback when empty set is passed.

        # Contract: streaming-contract:SessionLifecycle:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_error_event,
        )

        # Empty set MUST fall back to hardcoded defaults
        assert is_error_event("session.error", error_events=set()) is True
        assert is_error_event("error", error_events=set()) is True

    def test_is_usage_event_empty_set_uses_fallback(self) -> None:
        """is_usage_event MUST use fallback when empty set is passed.

        # Contract: streaming-contract:SessionLifecycle:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_usage_event,
        )

        # Empty set MUST fall back to hardcoded defaults
        assert is_usage_event("assistant.usage", usage_events=set()) is True
        assert is_usage_event("usage_update", usage_events=set()) is True


class TestEventHelpersEdgeCases:
    """Tests for edge cases and None handling in event helpers.

    Contract: event-vocabulary:Classification:MUST:1 — all helpers handle None safely.
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


class TestUsageEventHelpers:
    """Tests for usage event helpers.

    Contract: streaming-contract:usage:MUST:1 — usage events must be captured.
    Bug: Session 65131f78 showed zero usage when SDK sent assistant.usage after session.idle.
    """

    def test_is_usage_event_matches_assistant_usage(self) -> None:
        """is_usage_event MUST match assistant.usage.

        # Contract: streaming-contract:usage:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_usage_event,
        )

        # These MUST match
        assert is_usage_event("assistant.usage") is True
        assert is_usage_event("usage_update") is True  # Legacy format
        assert is_usage_event("ASSISTANT.USAGE") is True  # Case insensitive

    def test_is_usage_event_returns_false_for_none(self) -> None:
        """is_usage_event MUST return False for None input.

        # Contract: streaming-contract:usage:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_usage_event,
        )

        assert is_usage_event(None) is False

    def test_is_usage_event_does_not_match_unrelated(self) -> None:
        """is_usage_event MUST NOT match unrelated events.

        # Contract: streaming-contract:usage:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            is_usage_event,
        )

        assert is_usage_event("session.idle") is False
        assert is_usage_event("assistant.message") is False
        assert is_usage_event("usage_report") is False  # Different event

    def test_extract_usage_data_from_dict_event(self) -> None:
        """extract_usage_data extracts usage from dict events.

        # Contract: streaming-contract:usage:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        event = {"data": {"input_tokens": 100, "output_tokens": 50}}
        result = extract_usage_data(event)
        assert result is not None  # narrowed for pyright
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50

    def test_extract_usage_data_from_object_event(self) -> None:
        """extract_usage_data extracts usage from object events.

        # Contract: streaming-contract:usage:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        class MockData:
            input_tokens = 200
            output_tokens = 100

        class MockEvent:
            data = MockData()

        result = extract_usage_data(MockEvent())
        assert result is not None  # narrowed for pyright
        assert result["input_tokens"] == 200
        assert result["output_tokens"] == 100

    def test_extract_usage_data_returns_none_for_missing_data(self) -> None:
        """extract_usage_data returns None when no usage data present.

        # Contract: streaming-contract:usage:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        # Dict without usage fields
        assert extract_usage_data({"data": {}}) is None
        assert extract_usage_data({"data": {"other": "field"}}) is None

        # Object without usage fields
        class MockEvent:
            data = None

        assert extract_usage_data(MockEvent()) is None

    def test_extract_usage_data_handles_partial_usage(self) -> None:
        """extract_usage_data handles events with only one token field.

        # Contract: streaming-contract:usage:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        # Only input_tokens
        event = {"data": {"input_tokens": 100}}
        result = extract_usage_data(event)
        assert result is not None  # narrowed for pyright
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 0  # Defaults to 0

        # Only output_tokens
        event2 = {"data": {"output_tokens": 50}}
        result2 = extract_usage_data(event2)
        assert result2 is not None  # narrowed for pyright
        assert result2["input_tokens"] == 0  # Defaults to 0
        assert result2["output_tokens"] == 50

    def test_extract_usage_data_computes_total_tokens_from_dict_event(self) -> None:
        """Contract: streaming-contract:Usage:MUST — extract_usage_data MUST include
        total_tokens computed as input_tokens + output_tokens.

        # Contract: streaming-contract:usage:MUST:1
        The SDK assistant.usage event (session_events.py:874-877) sends only
        inputTokens and outputTokens — no totalTokens field. However, the kernel
        Usage model requires total_tokens: int (message_models.py:241, not Optional).
        Provider MUST compute total_tokens = input_tokens + output_tokens.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        event = {"data": {"input_tokens": 100, "output_tokens": 50}}
        result = extract_usage_data(event)
        assert result is not None  # narrowed for pyright
        assert result["total_tokens"] == 150, (
            f"total_tokens should be input+output=150, got {result.get('total_tokens')}"
        )

    def test_extract_usage_data_computes_total_tokens_from_object_event(self) -> None:
        """Contract: streaming-contract:Usage:MUST — object-path also computes total_tokens.

        # Contract: streaming-contract:usage:MUST:1
        Real SDK sends Usage object without total_tokens attribute; provider
        must compute it to satisfy kernel Usage.total_tokens: int requirement.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        class MockData:
            input_tokens = 200
            output_tokens = 75
            # Deliberately no total_tokens — mirrors real SDK Usage object

        class MockEvent:
            data = MockData()

        result = extract_usage_data(MockEvent())
        assert result is not None  # narrowed for pyright
        assert result["total_tokens"] == 275, (
            f"total_tokens should be input+output=275, got {result.get('total_tokens')}"
        )

    def test_extract_usage_data_includes_cache_read_tokens_from_dict_event(self) -> None:
        """Contract: streaming-contract:usage:MUST:2

        When the SDK assistant.usage event carries cacheReadTokens, extract_usage_data
        MUST return cache_read_tokens as an int in the result dict so the value can be
        forwarded to the kernel Usage object.

        Evidence: installed SDK session_events.py Data.cache_read_tokens is float|None,
        populated from obj.get("cacheReadTokens"). The kernel Usage.cache_read_tokens
        is int|None. Provider must bridge them with int conversion.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        event = {"data": {"input_tokens": 7432, "output_tokens": 500, "cache_read_tokens": 63128}}
        result = extract_usage_data(event)
        assert result is not None  # narrowed for pyright
        assert result["cache_read_tokens"] == 63128, (
            f"cache_read_tokens should be 63128, got {result.get('cache_read_tokens')}"
        )

    def test_extract_usage_data_includes_cache_read_tokens_from_object_event(self) -> None:
        """Contract: streaming-contract:usage:MUST:2

        Object-path (real SDK): extract_usage_data MUST read cache_read_tokens via
        getattr from the SDK Data object, matching the SDK's Data.cache_read_tokens
        field (session_events.py, float|None).
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        class MockData:
            input_tokens = 7432
            output_tokens = 500
            cache_read_tokens = 63128.0  # SDK sends float
            cache_write_tokens = None  # SDK does not currently populate this

        class MockEvent:
            data = MockData()

        result = extract_usage_data(MockEvent())
        assert result is not None  # narrowed for pyright
        assert result["cache_read_tokens"] == 63128, (
            f"Expected cache_read_tokens=63128 (int), got {result.get('cache_read_tokens')}"
        )
        assert result["cache_write_tokens"] is None, (
            f"Expected cache_write_tokens=None (SDK does not populate this field currently), "
            f"got {result.get('cache_write_tokens')}"
        )

    @pytest.mark.parametrize(
        "shape,reported_zero,expected",
        [
            pytest.param("dict", False, None, id="dict_absent_yields_none"),
            pytest.param("dict", True, 0, id="dict_explicit_zero_preserved"),
            pytest.param("object", False, None, id="object_absent_yields_none"),
            pytest.param("object", True, 0, id="object_explicit_zero_preserved"),
        ],
    )
    def test_extract_usage_data_cache_tokens_none_vs_zero(
        self, shape: str, reported_zero: bool, expected: int | None
    ) -> None:
        """Contract: streaming-contract:usage:MUST:2

        ``None`` (SDK did not report the field) MUST remain distinct from ``0``
        (SDK reported a confirmed zero). Conflating them hides whether caching
        occurred. Both event shapes must preserve the distinction.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        if shape == "dict":
            data: dict[str, object] = {"input_tokens": 100, "output_tokens": 50}
            if reported_zero:
                data["cache_read_tokens"] = 0
                data["cache_write_tokens"] = 0
            event: object = {"data": data}
        else:

            class _Data:
                input_tokens = 100
                output_tokens = 50

            if reported_zero:
                _Data.cache_read_tokens = 0.0  # type: ignore[attr-defined]
                _Data.cache_write_tokens = 0.0  # type: ignore[attr-defined]

            class _Event:
                data = _Data()

            event = _Event()

        result = extract_usage_data(event)
        assert result is not None  # narrowed for pyright
        assert result["cache_read_tokens"] == expected
        assert result["cache_write_tokens"] == expected

    def test_stream_accumulator_build_response_passes_cache_tokens_to_usage(self) -> None:
        """Contract: streaming-contract:usage:MUST:2

        StreamAccumulator.build_response() MUST pass cache_read_tokens and
        cache_write_tokens from the usage dict to the kernel Usage constructor,
        so the values appear in the ChatResponse returned to Amplifier.

        Mutation check: if build_response() omits cache_read_tokens from the Usage()
        call, this assertion turns red because result.usage.cache_read_tokens is None.
        """
        from amplifier_core import Usage

        from amplifier_module_provider_github_copilot.streaming import StreamingAccumulator

        acc = StreamingAccumulator()
        acc.usage = {
            "input_tokens": 7432,
            "output_tokens": 500,
            "total_tokens": 7932,
            "cache_read_tokens": 63128,
            "cache_write_tokens": None,
        }

        response = acc.to_chat_response()
        assert response.usage is not None  # narrowed for pyright
        assert isinstance(response.usage, Usage)
        assert response.usage.cache_read_tokens == 63128, (
            f"Expected cache_read_tokens=63128 in kernel Usage, "
            f"got {response.usage.cache_read_tokens}"
        )
        assert response.usage.cache_write_tokens is None, (
            "Expected cache_write_tokens=None "
            "(SDK does not currently populate this field for cache writes), "
            f"got {response.usage.cache_write_tokens}"
        )

    @pytest.mark.parametrize(
        "sdk_input,output,cache_read,cache_write,expected_input",
        [
            pytest.param(70436, 23, 63128, None, 70436, id="read_only_cache_write_absent"),
            # prod_cw_zero: cache_read > 0, cache_write explicitly 0. Distinct
            # from read_only_cache_write_absent (cw=None / field absent): here
            # cw=0 is explicit, exercising the None-vs-0 preservation path on
            # the cache_write field while leaving the subtraction a no-op.
            pytest.param(84119, 119, 60034, 0, 84119, id="prod_cw_zero"),
            # write_only_no_read: cache_read=0, cache_write > 0. Synthetic
            # shape that isolates the cache_write subtraction branch from
            # cache_read by zeroing the latter. Drives a non-trivial
            # subtraction even when the read bucket is inactive, so dropping
            # ``- (cache_write or 0)`` makes this row fail in isolation.
            pytest.param(64295, 473, 0, 64285, 10, id="write_only_no_read"),
            # mixed_real_shape: numbers scaled from a captured SDK v1.0.0b4
            # ``session.shutdown`` event (2026-05-17, model claude-sonnet-4.6,
            # captured after commit ``eab7989`` bumped the SDK from v0.3.0 to
            # v1.0.0b4 — the billing schema change in v1.0.0b4 is exactly what
            # made the gross-total interpretation of ``inputTokens`` load-bearing)
            # whose ``modelMetrics`` block carries inputTokens=34554,
            # cacheReadTokens=26075, cacheWriteTokens=8475 with a sibling
            # ``tokenDetails.input.tokenCount=4``; the identity
            # ``4 + 26075 + 8475 == 34554`` confirms ``inputTokens`` is the
            # gross billing total (fresh + cache_read + cache_write). This row
            # exercises the BOTH-cache-buckets-non-zero arithmetic path that
            # the production capture proves the SDK is capable of emitting.
            pytest.param(67719, 6, 60034, 7682, 60037, id="mixed_real_shape"),
        ],
    )
    def test_extract_usage_data_subtracts_only_cache_write_when_cache_hit_dict(
        self,
        sdk_input: int,
        output: int,
        cache_read: int,
        cache_write: int | None,
        expected_input: int,
    ) -> None:
        """Contract: streaming-contract:usage:MUST:3

        Behavioural contract: ``Usage.input_tokens ==
        max(0, sdk_inputTokens - (cache_write or 0))``; cache_read remains
        inside ``input_tokens`` (it is NOT subtracted), and the
        ``input_tokens + (cache_write or 0)`` round-trip MUST recover the SDK's
        original ``inputTokens`` value. The mixed and write-only rows kill
        mutations that the read-only fixture cannot reach: dropping the cache_write
        subtraction (write_only row), or accidentally subtracting cache_read
        (mixed row), both turn at least one assertion red.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        data: dict[str, object] = {
            "input_tokens": sdk_input,
            "output_tokens": output,
            "cache_read_tokens": cache_read,
        }
        if cache_write is not None:
            data["cache_write_tokens"] = cache_write
        result = extract_usage_data({"data": data})
        assert result is not None  # narrowed for pyright
        assert result["input_tokens"] == expected_input
        assert result["output_tokens"] == output
        assert result["total_tokens"] == expected_input + output
        assert result["cache_read_tokens"] == cache_read
        assert result["cache_write_tokens"] == cache_write
        # Round-trip: streaming-UI recovers SDK billing total via
        # input_tokens + (cache_write or 0).
        in_t = result["input_tokens"] or 0
        cw_t = result["cache_write_tokens"] or 0
        assert in_t + cw_t == sdk_input

    @pytest.mark.parametrize(
        "sdk_input,output,cache_read,cache_write,expected_input",
        [
            pytest.param(70436, 23, 63128.0, None, 70436, id="read_only_cache_write_absent"),
            # prod_cw_zero: see provenance note on the dict-path row above.
            pytest.param(84119, 119, 60034.0, 0.0, 84119, id="prod_cw_zero"),
            # write_only_no_read: see provenance note on the dict-path row above.
            pytest.param(64295, 473, 0.0, 64285.0, 10, id="write_only_no_read"),
            # mixed_real_shape: see provenance note on the dict-path row above.
            pytest.param(67719, 6, 60034.0, 7682.0, 60037, id="mixed_real_shape"),
        ],
    )
    def test_extract_usage_data_subtracts_only_cache_write_when_cache_hit_object(
        self,
        sdk_input: int,
        output: int,
        cache_read: float,
        cache_write: float | None,
        expected_input: int,
    ) -> None:
        """Contract: streaming-contract:usage:MUST:3

        Object-path (attribute-bearing stand-in mimicking the SDK
        ``session_events.Data`` shape; ``float | None`` cache fields). Same
        behavioural contract as the dict path: cache_read stays inside
        ``input_tokens`` and only cache_write is subtracted, clamped at zero.
        The object-path branch in ``extract_usage_data`` is physically distinct
        from the dict-path branch (separate ``getattr`` reads vs. ``dict.get``),
        so both must be exercised independently.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        class MockData:
            pass

        MockData.input_tokens = sdk_input  # type: ignore[attr-defined]
        MockData.output_tokens = output  # type: ignore[attr-defined]
        MockData.cache_read_tokens = cache_read  # type: ignore[attr-defined]
        MockData.cache_write_tokens = cache_write  # type: ignore[attr-defined]

        class MockEvent:
            data = MockData()

        result = extract_usage_data(MockEvent())
        assert result is not None  # narrowed for pyright
        assert result["input_tokens"] == expected_input
        assert result["output_tokens"] == output
        assert result["total_tokens"] == expected_input + output
        assert result["cache_read_tokens"] == int(cache_read)
        expected_cw = int(cache_write) if cache_write is not None else None
        assert result["cache_write_tokens"] == expected_cw
        in_t = result["input_tokens"] or 0
        cw_t = result["cache_write_tokens"] or 0
        assert in_t + cw_t == sdk_input

    @pytest.mark.parametrize(
        "shape",
        ["dict", "object"],
    )
    def test_extract_usage_data_clamps_input_to_zero_when_cache_write_exceeds_input(
        self, shape: str
    ) -> None:
        """Contract: streaming-contract:usage:MUST:3

        The MUST clause requires the result to be ``clamped to zero`` when the
        cache_write subtraction would underflow. Without ``max(0, ...)`` the
        kernel ``Usage.input_tokens`` would be negative, breaking downstream
        billing math. This is the only test that exercises the clamp branch.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        if shape == "dict":
            event: object = {
                "data": {
                    "input_tokens": 100,
                    "output_tokens": 5,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 250,
                }
            }
        else:

            class _Data:
                input_tokens = 100
                output_tokens = 5
                cache_read_tokens = 0.0
                cache_write_tokens = 250.0

            class _Event:
                data = _Data()

            event = _Event()

        result = extract_usage_data(event)
        assert result is not None  # narrowed for pyright
        assert result["input_tokens"] == 0, (
            "Cache-write underflow MUST clamp input_tokens to 0, not "
            f"{result.get('input_tokens')}"
        )
        assert result["total_tokens"] == 5, (
            "total_tokens = clamped_input + output = 0 + 5"
        )

    def test_extract_usage_data_input_tokens_unchanged_when_no_cache(self) -> None:
        """Contract: streaming-contract:usage:MUST:3

        When no cache activity (cache_read_tokens is None), input_tokens = sdk value
        unchanged (cold cache — sdk value IS the fresh portion).
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        event = {"data": {"input_tokens": 100, "output_tokens": 50}}
        result = extract_usage_data(event)
        assert result is not None  # narrowed for pyright
        assert result["input_tokens"] == 100, (
            "When no cache, input_tokens should equal sdk value (no subtraction)"
        )
        assert result["total_tokens"] == 150


class TestStreamingUIPercentageInvariantWithRealCapturedShapes:
    """Anti-1633% regression: the streaming-ui hook's cache-percentage display
    must never exceed 100%.

    Contract: streaming-contract:usage:MUST:3 (kernel-mandated gross input shape)
    Anchor (upstream): amplifier-core PROVIDER_CONTRACT.md L176-187 -- input_tokens
    "MUST" be "gross total (fresh + cache_read combined)".
    Anchor (downstream): amplifier-module-hooks-streaming-ui __init__.py L74-96 --
    `_compute_total_input` returns `input_tokens + cache_create`, then displays
    `cache_pct = int((cache_read / total_input) * 100)`.

    Why this class exists separately from the per-row parametrize tables above:
    those rows cover the post-transform field values. This class enforces the
    end-to-end ANTI-1633% invariant -- that for every shape the SDK can plausibly
    emit, the post-`extract_usage_data` Usage dict, when fed into the streaming-ui
    formula, produces a percentage in [0, 100].

    Shapes are CAPTURED FROM LIVE amplifier runs against the github-copilot SDK
    (4 distinct production shapes plus one defensive all-fields-None shape;
    identities verified by replaying the kernel formula). Each shape pairs the
    SDK-side raw fields with the kernel-mandated post-transform result.

    Cited by ``extract_usage_data`` docstring in
    ``amplifier_module_provider_github_copilot/sdk_adapter/event_helpers.py``
    as the assistant.usage proof chain for streaming-contract:usage:MUST:3 --
    keep class name in sync if renamed.
    """

    # Five live-captured shapes from `amplifier run` probe matrix:
    #   (1) claude-sonnet text-only mid-session cache hit
    #   (2) claude-sonnet tool-using turn (tool_calls > 0)
    #   (3) claude-haiku WRITE-ONLY first turn (huge cache_write, no cache_read)
    #   (4) gpt-5.5 no-caching turn (cache fields zero across the board)
    #   (5) defensive: SDK emitted Usage with all fields None
    # Each row: (label, sdk_input, sdk_cache_read, sdk_cache_write, sdk_output,
    # expected_input_after_transform, expected_total_after_transform).
    CAPTURED_SHAPES = [
        ("claude_sonnet_cache_hit", 63390, 60068, 3319, 6, 60071, 60077),
        ("claude_sonnet_tool_use", 63393, 60068, 3322, 90, 60071, 60161),
        ("claude_haiku_write_only", 63552, 0, 63542, 96, 10, 106),
        ("gpt55_no_cache", 53611, 0, 0, 58, 53611, 53669),
        ("all_none_defensive", None, None, None, None, None, None),
    ]

    @pytest.mark.parametrize(
        "label,sdk_input,sdk_cr,sdk_cw,sdk_out,exp_in,exp_total",
        CAPTURED_SHAPES,
        ids=[r[0] for r in CAPTURED_SHAPES],
    )
    def test_real_captured_shape_satisfies_streaming_ui_invariant(
        self,
        label: str,
        sdk_input: int | None,
        sdk_cr: int | None,
        sdk_cw: int | None,
        sdk_out: int | None,
        exp_in: int | None,
        exp_total: int | None,
    ) -> None:
        """For every captured production shape, the streaming-ui denominator
        (`input_tokens + cache_write_tokens`) must be >= cache_read_tokens.

        This is the direct anti-regression assertion for the 1633%-display bug.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        event = {
            "data": {
                "input_tokens": sdk_input,
                "output_tokens": sdk_out,
                "cache_read_tokens": sdk_cr,
                "cache_write_tokens": sdk_cw,
            }
        }
        result = extract_usage_data(event)

        if sdk_input is None and sdk_out is None:
            # Defensive: SDK emitted a Usage event with no numbers.
            # The helper should either return None or a Usage with input=None.
            # The streaming-ui hook coerces None to 0 (`_compute_total_input` L90-96)
            # and the percentage display path is gated on `total_input > 0`, so
            # no division-by-zero crash and no percentage shown -- acceptable.
            if result is not None:
                # If a Usage was synthesised, its input_tokens must be 0 or None,
                # and cache_read must be 0 or None.
                assert (result.get("input_tokens") or 0) == 0
                assert (result.get("cache_read_tokens") or 0) == 0
            return

        assert isinstance(result, dict), (
            f"shape={label}: extract_usage_data returned {type(result).__name__}, expected dict"
        )
        assert result["input_tokens"] == exp_in, (
            f"shape={label}: post-transform input_tokens "
            f"expected {exp_in}, got {result['input_tokens']}"
        )
        assert result["total_tokens"] == exp_total, (
            f"shape={label}: total_tokens expected {exp_total}, got {result['total_tokens']}"
        )

        # The streaming-ui invariant: denominator must be >= numerator.
        # Denominator = _compute_total_input = input_tokens + cache_write_tokens
        # Numerator   = cache_read_tokens
        input_tokens = result["input_tokens"] or 0
        cache_read = result.get("cache_read_tokens") or 0
        cache_write = result.get("cache_write_tokens") or 0
        denom = input_tokens + cache_write

        assert denom >= cache_read, (
            f"shape={label}: streaming-ui denominator ({denom}) < cache_read ({cache_read}); "
            "this would produce a >100% display (the 1633% regression)"
        )
        if denom > 0:
            pct = (cache_read / denom) * 100
            assert 0 <= pct <= 100, (
                f"shape={label}: cache percentage {pct:.2f}% outside [0, 100]"
            )

    def test_round_trip_identity_holds_for_all_captured_shapes(self) -> None:
        """For every non-degenerate captured shape, the SDK-side gross input
        must equal (post-transform input_tokens) + (cache_write_tokens).

        This is the identity that proves `extract_usage_data` only subtracts
        cache_write -- not cache_read.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        for label, sdk_in, sdk_cr, sdk_cw, sdk_out, _exp_in, _exp_total in (
            self.CAPTURED_SHAPES
        ):
            if sdk_in is None:
                continue  # degenerate row covered by parametrized test above
            event = {
                "data": {
                    "input_tokens": sdk_in,
                    "output_tokens": sdk_out,
                    "cache_read_tokens": sdk_cr,
                    "cache_write_tokens": sdk_cw,
                }
            }
            result = extract_usage_data(event)
            assert isinstance(result, dict)
            it = result["input_tokens"] or 0
            cw = result.get("cache_write_tokens") or 0
            assert it + cw == sdk_in, (
                f"shape={label}: round-trip identity violated: "
                f"input_tokens({it}) + cache_write({cw}) != sdk_input({sdk_in})"
            )

    def test_gpt55_no_cache_shape_displays_no_percentage(self) -> None:
        """gpt-5.5 produced (cr=0, cw=0). Streaming-ui must not display a cache %
        on this shape -- there is nothing to display. The numerator is 0, so any
        well-formed display formula yields 0% (or suppresses entirely).
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        event = {
            "data": {
                "input_tokens": 53611,
                "output_tokens": 58,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            }
        }
        result = extract_usage_data(event)
        assert isinstance(result, dict)
        assert result["input_tokens"] == 53611, "no-cache shape: input must pass through unchanged"
        assert result["cache_read_tokens"] == 0
        assert result["cache_write_tokens"] == 0
        # streaming-ui formula: pct = cr / (it + cw) = 0 / 53611 = 0.0
        denom = (result["input_tokens"] or 0) + (result.get("cache_write_tokens") or 0)
        assert denom == 53611
        pct = (result.get("cache_read_tokens") or 0) / denom * 100
        assert pct == 0.0

    def test_haiku_write_only_first_turn_shape(self) -> None:
        """claude-haiku first-turn write-only: SDK input=63552 with cw=63542, cr=0.
        This is the WRITE phase before any cache reads occur. Post-transform
        input_tokens must collapse to the fresh portion (10).
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.event_helpers import (
            extract_usage_data,
        )

        event = {
            "data": {
                "input_tokens": 63552,
                "output_tokens": 96,
                "cache_read_tokens": 0,
                "cache_write_tokens": 63542,
            }
        }
        result = extract_usage_data(event)
        assert isinstance(result, dict)
        assert result["input_tokens"] == 10, (
            "haiku write-only first turn: post-transform input = sdk_input - cache_write"
        )
        # Streaming-ui denom = 10 + 63542 = 63552; numerator (cache_read) = 0.
        denom = (result["input_tokens"] or 0) + (result.get("cache_write_tokens") or 0)
        assert denom == 63552
        pct = (result.get("cache_read_tokens") or 0) / denom * 100
        assert pct == 0.0


class TestValidateNoClassificationOverlapValidator:
    """Direct unit tests for every raise path in _validate_no_classification_overlap.

    Contract: event-vocabulary:Classification:MUST:1 — each event type has exactly
    one classification. The validator must raise ConfigurationError on any overlap.

    Tests call _validate_no_classification_overlap directly with Python structures.
    No YAML, no file I/O — this verifies the validator logic in isolation.
    """

    def test_bridge_and_consume_exact_overlap_raises(self) -> None:
        """Bridge key that also appears in consume_patterns must raise.

        # Contract: event-vocabulary:Classification:MUST:1
        Line 404 in streaming.py: bridge vs consume exact match branch.
        """
        bridge: dict[str, tuple[DomainEventType, str | None]] = {
            "session.idle": (DomainEventType.TURN_COMPLETE, None)
        }
        consume = ["session.idle"]  # Exact key in bridge

        with pytest.raises(ConfigurationError, match="both BRIDGE and CONSUME"):
            _validate_no_classification_overlap(bridge, consume, [])

    def test_bridge_and_drop_exact_overlap_raises(self) -> None:
        """Bridge key that also appears in drop_patterns must raise.

        # Contract: event-vocabulary:Classification:MUST:1
        Line 413 in streaming.py: bridge vs drop exact match branch.
        """
        bridge: dict[str, tuple[DomainEventType, str | None]] = {
            "assistant.message": (DomainEventType.TURN_COMPLETE, None)
        }
        drop = ["assistant.message"]  # Exact key in bridge

        with pytest.raises(ConfigurationError, match="both BRIDGE and DROP"):
            _validate_no_classification_overlap(bridge, [], drop)

    def test_consume_and_drop_exact_overlap_raises(self) -> None:
        """Pattern in both consume_patterns and drop_patterns must raise.

        # Contract: event-vocabulary:Classification:MUST:1
        Line 423 in streaming.py: consume vs drop exact match branch.
        """
        consume = ["tool.call"]
        drop = ["tool.call"]  # Same in both

        with pytest.raises(ConfigurationError, match="both CONSUME and DROP"):
            _validate_no_classification_overlap({}, consume, drop)

    def test_bridge_type_matches_drop_wildcard_raises(self) -> None:
        """Bridge event type matched by a drop wildcard pattern must raise.

        # Contract: event-vocabulary:Classification:MUST:1
        Line 434 in streaming.py: bridge type vs drop wildcard branch.
        """
        bridge: dict[str, tuple[DomainEventType, str | None]] = {
            "system.notification": (DomainEventType.TURN_COMPLETE, None)
        }
        drop = ["system.*"]  # Wildcard covers the bridge type

        with pytest.raises(ConfigurationError, match="matches DROP wildcard"):
            _validate_no_classification_overlap(bridge, [], drop)

    def test_bridge_type_matches_consume_wildcard_raises(self) -> None:
        """Bridge event type matched by a consume wildcard pattern must raise.

        # Contract: event-vocabulary:Classification:MUST:1
        Line 442 in streaming.py: bridge type vs consume wildcard branch.
        """
        bridge: dict[str, tuple[DomainEventType, str | None]] = {
            "session.idle": (DomainEventType.TURN_COMPLETE, None)
        }
        consume = ["session.*"]  # Wildcard covers the bridge type

        with pytest.raises(ConfigurationError, match="matches CONSUME wildcard"):
            _validate_no_classification_overlap(bridge, consume, [])

    def test_consume_entry_matches_drop_wildcard_raises(self) -> None:
        """Explicit consume entry matched by a drop wildcard must raise.

        # Contract: event-vocabulary:Classification:MUST:1
        Line 454 in streaming.py: consume entry vs drop wildcard branch.
        """
        consume = ["tool.call"]  # Explicit (no wildcard)
        drop = ["tool.*"]  # Wildcard covers tool.call

        with pytest.raises(ConfigurationError, match="matches DROP wildcard"):
            _validate_no_classification_overlap({}, consume, drop)

    def test_drop_entry_matches_consume_wildcard_raises(self) -> None:
        """Explicit drop entry matched by a consume wildcard must raise.

        # Contract: event-vocabulary:Classification:MUST:1
        Line 466 in streaming.py: drop entry vs consume wildcard branch.
        """
        consume = ["assistant.*"]  # Wildcard consume pattern
        drop = ["assistant.finished"]  # Explicit drop, matched by consume wildcard

        with pytest.raises(ConfigurationError, match="matches CONSUME wildcard"):
            _validate_no_classification_overlap({}, consume, drop)

    def test_valid_disjoint_config_does_not_raise(self) -> None:
        """Fully disjoint bridge/consume/drop must not raise (false-positive guard).

        # Contract: event-vocabulary:Classification:MUST:1
        """
        bridge: dict[str, tuple[DomainEventType, str | None]] = {
            "session.idle": (DomainEventType.TURN_COMPLETE, None)
        }
        consume = ["tool.call", "tool.result"]
        drop = ["unknown.*", "vendor.*"]

        # Must not raise
        _validate_no_classification_overlap(bridge, consume, drop)


class TestEmptyIdleEventsRaises:
    """Validate that load_event_config raises on empty session_lifecycle.idle_events.

    Contract: streaming-contract:SessionLifecycle:MUST:1 — provider cannot detect
    session completion without idle_events. This is fail-fast at load time.

    Line 548 in streaming.py: raise ConfigurationError when idle_event_types is empty.
    """

    def test_empty_idle_events_raises_configuration_error(self, tmp_path: Path) -> None:
        """events.yaml with empty idle_events must raise ConfigurationError.

        # Contract: streaming-contract:SessionLifecycle:MUST:1
        This is the session-hang prevention guard. An empty idle_events set means
        the provider can never detect session.idle, causing infinite wait.
        """
        import yaml

        # Minimal YAML with empty idle_events — triggers the fail-fast guard
        bad_yaml: dict[str, object] = {
            "event_classifications": {
                "bridge": [],
                "consume": [],
                "drop": [],
            },
            "finish_reasons": {},
            "streaming_emission": {},
            "session_lifecycle": {
                "idle_events": [],  # Empty — must raise
                "error_events": ["session.error"],
                "usage_events": ["assistant.usage"],
            },
        }
        config_file = tmp_path / "events.yaml"
        config_file.write_text(yaml.dump(bad_yaml), encoding="utf-8")

        with pytest.raises(ConfigurationError, match="session_lifecycle.idle_events"):
            load_event_config(config_path=config_file)


class TestNoisySdkEventsClassifiedWithoutWarning:
    """SDK events observed in live runs that must be classified silently.

    Contract: event-vocabulary:Drop:MUST:2
    Both event types are current SDK SessionEventType enum members (SDK snapshot
    2026-04-02). They emit during normal session init and produce WARNING logs when
    absent from events.yaml. They have no domain value for Amplifier.
    """

    def test_session_skills_loaded_classified_as_drop_without_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """session.skills_loaded must be DROP and must not emit an Unknown warning.

        Contract: event-vocabulary:Drop:MUST:2

        The skill.* wildcard in events.yaml does NOT match session.skills_loaded
        (fnmatch requires the prefix to match). Without an explicit entry the event
        falls through to the logger.warning() branch, producing noise in every live
        session. The entry must silence it.
        """
        import logging

        from amplifier_module_provider_github_copilot.streaming import (
            EventClassification,
            classify_event,
        )

        config = load_event_config()
        streaming_logger = "amplifier_module_provider_github_copilot.streaming"

        with caplog.at_level(logging.WARNING, logger=streaming_logger):
            result = classify_event("session.skills_loaded", config)

        assert result == EventClassification.DROP, (
            f"session.skills_loaded must be DROP, got {result}"
        )
        assert "Unknown SDK event type" not in caplog.text, (
            "session.skills_loaded must not produce an Unknown SDK event type warning"
        )

    def test_system_message_classified_as_drop_without_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """system.message must be DROP and must not emit an Unknown warning.

        Contract: event-vocabulary:Drop:MUST:2

        system.message is SDK SystemMessageEvent — carries system/developer prompt
        text injected into the conversation. It has no domain value for Amplifier
        and must not be forwarded or logged (contains prompt content).
        system.notification is already in consume; system.message is a distinct
        event type and does not match the consume entry.
        """
        import logging

        from amplifier_module_provider_github_copilot.streaming import (
            EventClassification,
            classify_event,
        )

        config = load_event_config()
        streaming_logger = "amplifier_module_provider_github_copilot.streaming"

        with caplog.at_level(logging.WARNING, logger=streaming_logger):
            result = classify_event("system.message", config)

        assert result == EventClassification.DROP, f"system.message must be DROP, got {result}"
        assert "Unknown SDK event type" not in caplog.text, (
            "system.message must not produce an Unknown SDK event type warning"
        )
