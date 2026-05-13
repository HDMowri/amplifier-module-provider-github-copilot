"""Tests for SDK event classification gaps.

Contract anchors:
- event-vocabulary:Classification:MUST:1 (each event has exactly one classification)
- event-vocabulary:Drop:MUST:2 (no SDK enum member produces "Unknown SDK event type" warning)

Locks in that every SDK ``SessionEventType`` enum member is explicitly
classified (BRIDGE/CONSUME/DROP) and never falls through to the
"Unknown SDK event type" warning in ``streaming.py``.

Note on SDK availability: ``github-copilot-sdk`` is a hard runtime
dependency of this provider (``pyproject.toml`` install_requires). Tests
in this file import ``copilot.generated.session_events.SessionEventType``
unconditionally; if the import fails, that is a developer-environment
defect (see README "Prerequisites") and the test SHOULD fail loudly
rather than silently skip.
"""

from __future__ import annotations

import logging

import pytest

from amplifier_module_provider_github_copilot.streaming import (
    EventClassification,
    classify_event,
    load_event_config,
)

# ----------------------------------------------------------------------------
# T1: meta-test — every live SDK SessionEventType is classified
# ----------------------------------------------------------------------------


class TestEventClassificationCoversLiveSDKEnum:
    """Every member of the live SDK ``SessionEventType`` enum MUST classify
    without producing the "Unknown SDK event type" warning.

    Contract anchors:
    - event-vocabulary:Classification:MUST:1
    - event-vocabulary:Drop:MUST:2 (primary — this test enforces "no unknown
      warning for any SDK enum member")

    Mutation check: removing any explicit entry (e.g., ``commands.changed``)
    from events.yaml makes the corresponding enum member fall through to the
    unknown-event warning — red.

    Drift guard: if the SDK enum shrinks below ten string members, the
    canonical import path likely moved or the SDK was partially installed;
    the test fails loudly rather than silently providing thin coverage.
    """

    @staticmethod
    def _live_sdk_event_type_values() -> list[str]:
        """Return the live SDK ``SessionEventType`` string members.

        SDK 0.3.0 ships ``SessionEventType`` at
        ``copilot.generated.session_events`` (NOT ``copilot.session``); see
        the SDK source at ``copilot/generated/session_events.py:106``. The
        canonical generated path is the single source of truth; an
        ``ImportError`` here means the SDK is not installed and the
        developer needs to fix their environment per README "Prerequisites".
        """
        from copilot.generated.session_events import (  # type: ignore[import-not-found]
            SessionEventType,
        )

        values: list[str] = []
        for member in SessionEventType:
            value = member.value
            if isinstance(value, str) and value != "unknown":
                values.append(value)
        return values

    def test_no_unknown_warnings_for_real_sdk_event_types(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        live_values = self._live_sdk_event_type_values()
        # Drift guard: SDK 0.3.0 ships 70+ string members. If the live enum
        # has fewer than ten, the canonical import path likely moved or the
        # SDK is partially installed — fail loudly, never silently.
        assert len(live_values) >= 10, (
            f"copilot.generated.session_events.SessionEventType yielded only "
            f"{len(live_values)} string members; SDK 0.3.0 ships 70+. "
            f"Investigate: SDK partially installed, or the canonical enum "
            f"location moved."
        )
        config = load_event_config()
        unknown: list[str] = []
        with caplog.at_level(
            logging.WARNING,
            logger="amplifier_module_provider_github_copilot.streaming",
        ):
            for value in live_values:
                caplog.clear()
                classification = classify_event(value, config)
                assert classification in (
                    EventClassification.BRIDGE,
                    EventClassification.CONSUME,
                    EventClassification.DROP,
                )
                if any(
                    "Unknown SDK event type" in rec.message
                    for rec in caplog.records
                ):
                    unknown.append(value)

        assert not unknown, (
            f"SDK SessionEventType members fell through to the unknown-event "
            f"warning instead of an explicit classification: {unknown!r}. "
            f"Add each to events.yaml under bridge_mappings/consume/drop. "
            f"This meta-test is the gate that prevents silent classification "
            f"gaps when the SDK enum grows."
        )


# ----------------------------------------------------------------------------
# T2: commands.changed (plural) — explicit DROP, no unknown warning
# ----------------------------------------------------------------------------


class TestExplicitDropEntriesEmitNoUnknownWarning:
    """Explicit DROP entries — ``commands.changed`` plus the SDK 0.3.0 enum
    members added in this PR — MUST classify as DROP and MUST NOT trigger
    the "Unknown SDK event type" warning in ``streaming.py``.

    The plural ``commands.changed`` is NOT matched by the existing
    ``command.*`` (singular) wildcard, so it requires its own literal entry.
    The SDK 0.3.0 entries (``auto_mode_switch.*``, ``mcp.oauth_*``,
    ``sampling.*``, several ``session.*`` lifecycle events) likewise have
    no domain value for amplifier-core and require explicit DROP.

    Contract anchors:
    - event-vocabulary:Classification:MUST:1
    - event-vocabulary:Drop:MUST:2
    """

    def test_commands_changed_drops_without_unknown_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        config = load_event_config()
        with caplog.at_level(
            logging.WARNING,
            logger="amplifier_module_provider_github_copilot.streaming",
        ):
            result = classify_event("commands.changed", config)
        assert result == EventClassification.DROP
        assert not any(
            "Unknown SDK event type" in rec.message for rec in caplog.records
        ), (
            "commands.changed produced the unknown-event warning despite an "
            "explicit DROP entry in events.yaml; check that the entry is "
            "present and not shadowed."
        )

    @pytest.mark.parametrize(
        "event_type",
        [
            # SDK 0.3.0 enum members
            # (copilot.generated.session_events.SessionEventType) that fell
            # through to the unknown-event warning before this PR added
            # explicit DROP entries.
            "auto_mode_switch.requested",
            "auto_mode_switch.completed",
            "mcp.oauth_required",
            "mcp.oauth_completed",
            "sampling.requested",
            "sampling.completed",
            "session.extensions_loaded",
            "session.mcp_servers_loaded",
            "session.mcp_server_status_changed",
            "session.remote_steerable_changed",
        ],
    )
    def test_sdk_030_event_types_classified_without_warning(
        self, caplog: pytest.LogCaptureFixture, event_type: str
    ) -> None:
        """SDK 0.3.0 enum members added to DROP must classify as DROP without
        producing the "Unknown SDK event type" warning.

        Each event below was observed to fall through to the
        ``"Unknown SDK event type"`` WARNING path in ``streaming.py`` before
        this PR's events.yaml additions. This test pins the explicit DROP
        classifications so removing any one entry surfaces here as a red test.

        Mutation check (per `testing.instructions.md`): delete any single
        event from the DROP block in events.yaml — the matching parameter
        case here goes red on BOTH the classification equality assertion
        AND the "no unknown warning" assertion.

        Contract anchors:
        - event-vocabulary:Classification:MUST:1
        - event-vocabulary:Drop:MUST:2
        """
        config = load_event_config()
        with caplog.at_level(
            logging.WARNING,
            logger="amplifier_module_provider_github_copilot.streaming",
        ):
            classification = classify_event(event_type, config)
        # Assert exact DROP, not merely "no warning": a regression that
        # classifies the event as BRIDGE/CONSUME but still avoids the
        # unknown-event warning would silently corrupt the streaming contract.
        assert classification == EventClassification.DROP, (
            f"{event_type!r} classified as {classification.name} but should be "
            f"DROP. This event has no domain value for amplifier-core; "
            f"forwarding it as BRIDGE/CONSUME would corrupt the streaming "
            f"contract."
        )
        assert not any(
            "Unknown SDK event type" in rec.message for rec in caplog.records
        ), f"{event_type!r} fell through to unknown-event warning"


