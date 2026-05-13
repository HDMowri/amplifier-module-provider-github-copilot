"""Type stubs for ``copilot.client`` submodule (SDK v0.3.0).

The live SDK defines ``SubprocessConfig`` here and re-exports it from the
``copilot`` root. The provider imports it from the root path; tests sometimes
import it from ``copilot.client`` directly. ``ReasoningEffort`` is declared
in ``copilot.session`` and re-exported from ``copilot.client``; the live SDK
exposes the identical Literal object at both module paths
(``copilot.session.ReasoningEffort is copilot.client.ReasoningEffort`` →
True, verified against installed wheel). The drift test
``TestReasoningEffortReExportedAtSessionPath`` in
``tests/test_sdk_assumptions.py`` pins this invariant.

Verified against live SDK on 2026-05-12.
"""

from typing import Literal

from .types import SubprocessConfig

ReasoningEffort = Literal["low", "medium", "high", "xhigh"]

__all__ = ["ReasoningEffort", "SubprocessConfig"]
