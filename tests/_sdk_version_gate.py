"""SDK dist-version gate for tests.

Policy: FAIL (never skip) if ``github-copilot-sdk`` dist version != pinned
version. Uses ``importlib.metadata.version()`` — not ``copilot.__version__``,
which is hardcoded in the SDK source and does not reflect the installed dist
version.

The pinned version is parsed from the ``github-copilot-sdk==<version>`` entry
in ``pyproject.toml`` — the single tracked source of truth for the SDK pin.
"""

from __future__ import annotations

import tomllib
from importlib.metadata import version as _dist_version_lookup
from pathlib import Path
from typing import Any

import pytest

_SDK_DIST = "github-copilot-sdk"


def _pinned_version() -> str:
    """Return the SDK version pinned by ``pyproject.toml``.

    Parses the ``[project].dependencies`` array for an exact-pin entry of
    the form ``github-copilot-sdk==<version>``. Raises ``RuntimeError`` if
    the dependency is missing or not exact-pinned, because a floating pin
    would defeat the purpose of this gate.
    """
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", [])
    prefix = f"{_SDK_DIST}=="
    for entry in deps:
        if isinstance(entry, str) and entry.startswith(prefix):
            return entry[len(prefix) :].strip()
    raise RuntimeError(
        f"Exact pin '{_SDK_DIST}==<version>' not found in {pyproject} "
        f"[project].dependencies."
    )


def require_sdk() -> Any:
    """Fail (never skip) if SDK is missing or wrong dist version. Return the module.

    Policy: tests run and FAIL on version mismatch; see test_live_smoke.py:43-46.
    The required version is read from the ``github-copilot-sdk`` entry in
    ``pyproject.toml`` — the tracked source of truth for the SDK pin.
    """
    import copilot  # ImportError propagates as test error if SDK not installed

    dist_version = _dist_version_lookup("github-copilot-sdk")
    required = _pinned_version()
    if dist_version != required:
        pytest.fail(
            f"github-copilot-sdk dist version {dist_version!r} != required {required!r}. "
            f"Install the pinned SDK: pip install 'github-copilot-sdk=={required}'"
        )
    return copilot
