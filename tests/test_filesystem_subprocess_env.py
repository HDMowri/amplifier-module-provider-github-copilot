"""Wiring:MUST:1, MUST:2, MUST:5 — CopilotClient constructor contract.

Contract: contracts/filesystem-layout.md
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from amplifier_module_provider_github_copilot.config._paths import (
    ProviderPaths,
)

ENV_VAR_NAME = "AMPLIFIER_PROVIDER_GITHUB_COPILOT_HOME"


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for k in (
        ENV_VAR_NAME,
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "LOCALAPPDATA",
        "COPILOT_HOME",
        "COPILOT_CLI_PATH",
    ):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def _stub_copilot_client():
    """Return a stub CopilotClient class for tests."""
    constructor_calls: list[dict[str, Any]] = []

    class FakeCopilotClient:
        def __init__(
            self,
            *,
            base_directory: str,
            github_token: str | None = None,
            log_level: str = "info",
            env: dict[str, str],
            mode: str,
        ) -> None:
            constructor_calls.append(
                {
                    "base_directory": base_directory,
                    "github_token": github_token,
                    "log_level": log_level,
                    "env": env,
                    "mode": mode,
                }
            )

        async def start(self) -> None:  # pragma: no cover - not invoked
            pass

    return FakeCopilotClient, constructor_calls


# Contract: filesystem-layout:Wiring:MUST:1
@pytest.mark.asyncio
async def test_token_branch_passes_provider_home_to_sdk(
    clean_env: pytest.MonkeyPatch, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token branch must call CopilotClient with
    base_directory=str(load_provider_paths().provider_home).
    """
    target_home = tmp_path / "wiring-home"
    # Override the autouse sandbox so we control the value the wrapper sees.
    sentinel = ProviderPaths(provider_home=target_home, cache_home=tmp_path / "wcache")
    monkeypatch.setattr(
        "amplifier_module_provider_github_copilot.config._paths.load_provider_paths",
        lambda: sentinel,
    )
    # Note: client.py imports load_provider_paths via a function-local
    # `from ..config._paths import ... load_provider_paths` inside
    # _ensure_client_initialized, so the patch above on
    # config._paths.load_provider_paths is the one that takes effect at
    # call time (function-local imports resolve through sys.modules).
    # No second module-level patch is needed.
    clean_env.setenv("GITHUB_TOKEN", "fake-token-for-wiring-test")

    FakeClient, constructor_calls = _stub_copilot_client()

    with patch(
        "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
        FakeClient,
    ):
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        w = CopilotClientWrapper()
        try:
            await w._ensure_client_initialized("test")
        except Exception:
            pass

    assert constructor_calls, "Token branch must have constructed CopilotClient"
    kwargs = constructor_calls[0]
    assert "base_directory" in kwargs, "Wiring:MUST:1 — base_directory kwarg missing"
    assert kwargs["base_directory"] == str(target_home), (
        f"base_directory must equal str(provider_home); got {kwargs['base_directory']!r}"
    )
    assert kwargs["mode"] == "copilot-cli", "Wiring:MUST:1 — mode must be copilot-cli"
    # Wiring:MUST:5 — cli_path MUST NOT be pinned (SDK falls back to bundled
    # binary once COPILOT_CLI_PATH is scrubbed). Catches RCE-class regression
    # where a future edit reintroduces explicit cli_path pinning.
    assert "cli_path" not in kwargs or kwargs.get("cli_path") is None, (
        f"cli_path MUST NOT be pinned; got {kwargs.get('cli_path')!r}"
    )


@pytest.mark.asyncio
async def test_base_directory_drives_copilot_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Provider wiring passes the isolated home through base_directory.

    Contract: filesystem-layout:Wiring:MUST:1, filesystem-layout:Wiring:MUST:5
    """
    from amplifier_module_provider_github_copilot.config._paths import ProviderPaths
    from amplifier_module_provider_github_copilot.sdk_adapter import client as client_mod

    captured_kwargs: dict[str, Any] = {}

    class FakeCopilotClient:
        def __init__(
            self,
            *,
            base_directory: str,
            log_level: str,
            env: dict[str, str],
            github_token: str | None = None,
            mode: str,
        ) -> None:
            captured_kwargs.update(
                {
                    "base_directory": base_directory,
                    "log_level": log_level,
                    "env": env,
                    "github_token": github_token,
                }
            )

        async def start(self) -> None:
            return None

    expected_home = tmp_path / "provider-home"
    paths = ProviderPaths(provider_home=expected_home, cache_home=tmp_path / "cache-home")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(client_mod, "CopilotClient", FakeCopilotClient)

    wrapper = client_mod.CopilotClientWrapper(provider_paths=paths)
    await wrapper._ensure_client_initialized(caller="test")  # pyright: ignore[reportPrivateUsage]

    assert captured_kwargs["base_directory"] == str(expected_home)


# Contract: filesystem-layout:Wiring:MUST:2
@pytest.mark.asyncio
async def test_token_and_no_token_branches_agree_on_copilot_home(
    clean_env: pytest.MonkeyPatch, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_home = tmp_path / "wiring-home-2"
    sentinel = ProviderPaths(provider_home=target_home, cache_home=tmp_path / "wcache2")
    monkeypatch.setattr(
        "amplifier_module_provider_github_copilot.config._paths.load_provider_paths",
        lambda: sentinel,
    )

    FakeClient, constructor_calls = _stub_copilot_client()

    with patch(
        "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
        FakeClient,
    ):
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        w1 = CopilotClientWrapper()
        try:
            await w1._ensure_client_initialized("test-no-token")
        except Exception:
            pass

        clean_env.setenv("GITHUB_TOKEN", "now-with-token")
        w2 = CopilotClientWrapper()
        try:
            await w2._ensure_client_initialized("test-with-token")
        except Exception:
            pass

    assert len(constructor_calls) >= 2
    h1 = constructor_calls[0].get("base_directory")
    h2 = constructor_calls[-1].get("base_directory")
    assert h1 == h2 == str(target_home), (
        f"Both branches must pass the same base_directory; got {h1!r} vs {h2!r}"
    )


# Contract: filesystem-layout:Wiring:MUST:5
@pytest.mark.asyncio
async def test_subprocess_env_omits_copilot_home_and_cli_path(
    clean_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """COPILOT_HOME and COPILOT_CLI_PATH must be scrubbed from
    CopilotClient env so the SDK never inherits them from the parent.
    """
    clean_env.setenv(ENV_VAR_NAME, str(tmp_path / "scrub-home"))
    clean_env.setenv("COPILOT_HOME", "/sentinel/host-copilot-home")
    clean_env.setenv("COPILOT_CLI_PATH", "/sentinel/host-copilot-cli")
    clean_env.setenv("PATH", os.environ.get("PATH", "/usr/bin"))

    FakeClient, constructor_calls = _stub_copilot_client()

    with patch(
        "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
        FakeClient,
    ):
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        w = CopilotClientWrapper()
        try:
            await w._ensure_client_initialized("test-env-scrub")
        except Exception:
            pass

    assert constructor_calls, "CopilotClient must be constructed"
    kwargs = constructor_calls[0]
    assert "env" in kwargs and isinstance(kwargs["env"], dict), (
        "Wiring:MUST:5 — CopilotClient env must be an explicit dict (not None)"
    )
    env = kwargs["env"]
    assert "COPILOT_HOME" not in env, (
        "Wiring:MUST:5 — COPILOT_HOME must be removed from spawned env"
    )
    assert "COPILOT_CLI_PATH" not in env, (
        "Wiring:MUST:5 — COPILOT_CLI_PATH must be removed from spawned env"
    )
    # PATH should survive — only the two hostile keys are scrubbed
    assert "PATH" in env, "Non-scrubbed env vars must be preserved"


@pytest.mark.asyncio
async def test_env_is_replace_not_merge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Provider wiring scrubs CLI-owned variables before SDK replacement env.

    Contract: filesystem-layout:Isolation:MUST:1
    """
    from amplifier_module_provider_github_copilot.config._paths import ProviderPaths
    from amplifier_module_provider_github_copilot.sdk_adapter import client as client_mod

    captured_kwargs: dict[str, Any] = {}

    class FakeCopilotClient:
        def __init__(
            self,
            *,
            base_directory: str,
            log_level: str,
            env: dict[str, str],
            github_token: str | None = None,
            mode: str,
        ) -> None:
            captured_kwargs.update(
                {
                    "base_directory": base_directory,
                    "log_level": log_level,
                    "env": env,
                    "github_token": github_token,
                }
            )

        async def start(self) -> None:
            return None

    paths = ProviderPaths(
        provider_home=tmp_path / "provider-home",
        cache_home=tmp_path / "cache-home",
    )
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("COPILOT_HOME", "ambient-home")
    monkeypatch.setenv("COPILOT_CLI_PATH", "ambient-cli")
    monkeypatch.setattr(client_mod, "CopilotClient", FakeCopilotClient)

    wrapper = client_mod.CopilotClientWrapper(provider_paths=paths)
    await wrapper._ensure_client_initialized(caller="test")  # pyright: ignore[reportPrivateUsage]

    assert "COPILOT_HOME" not in captured_kwargs["env"]
    assert "COPILOT_CLI_PATH" not in captured_kwargs["env"]


def test_scrub_sdk_env_removes_exactly_the_three_keys() -> None:
    """scrub_sdk_env() MUST remove the three SDK-overriding keys only.

    Both production wiring (sdk_adapter/client.py) and the live test fixture
    (tests/conftest.py) build their CopilotClient env via this helper, so the
    parity between them is mechanical. The pinned set is:

    - ``COPILOT_HOME`` — SDK injects from ``base_directory`` (b10
      ``client.py:3199``); ambient value would override the provider's
      explicit path wiring.
    - ``COPILOT_CLI_PATH`` — SDK resolves from the bundled binary it locates
      itself (b10 ``client.py:1202,1206``); ambient value would let a
      foreign binary execute under SDK identity.
    - ``COPILOT_SDK_AUTH_TOKEN`` — SDK only writes this into the spawned
      subprocess env when an explicit ``github_token`` is passed (b10
      ``client.py:3188-3189``); ambient value would otherwise survive into
      the child on the no-token branch and authenticate against a
      credential the provider never resolved (Auth:MUST:6 violation).

    Non-scrub rationale, ``COPILOT_MCP_APPS``: b10 also reads this env var
    as a process-level feature gate (b10 ``client.py:1707``), but the
    session-level ``create_session(enable_mcp_apps=False)`` default
    overrides it; the env gate only governs whether the runtime *can*
    honor the opt-in, not whether it auto-enables. If b10 semantics
    change so the env var becomes auto-enabling, add it here.

    If a future change adds another SDK-overriding env var, update
    SDK_ENV_SCRUB_KEYS and extend this test.

    Contract: filesystem-layout:Wiring:MUST:5, Auth:MUST:6
    """
    from amplifier_module_provider_github_copilot.sdk_adapter.client import (
        SDK_ENV_SCRUB_KEYS,
        scrub_sdk_env,
    )

    assert set(SDK_ENV_SCRUB_KEYS) == {
        "COPILOT_HOME",
        "COPILOT_CLI_PATH",
        "COPILOT_SDK_AUTH_TOKEN",
    }, (
        "If you intentionally added an SDK-overriding env var to scrub, update "
        "this test AND filesystem-layout:Wiring:MUST:5 in the same change."
    )

    source_env = {
        "COPILOT_HOME": "/sentinel/host-copilot-home",
        "COPILOT_CLI_PATH": "/sentinel/host-copilot-cli",
        "COPILOT_SDK_AUTH_TOKEN": "ghs_sentinel_ambient_token",
        "PATH": "/usr/bin",
        "GITHUB_TOKEN": "must-survive",
    }

    scrubbed = scrub_sdk_env(source_env)

    assert "COPILOT_HOME" not in scrubbed
    assert "COPILOT_CLI_PATH" not in scrubbed
    assert "COPILOT_SDK_AUTH_TOKEN" not in scrubbed
    assert scrubbed["PATH"] == "/usr/bin"
    assert scrubbed["GITHUB_TOKEN"] == "must-survive"
    # Input dict must not be mutated - callers pass dict(os.environ) and may
    # reuse the original.
    assert source_env["COPILOT_HOME"] == "/sentinel/host-copilot-home"
    assert source_env["COPILOT_SDK_AUTH_TOKEN"] == "ghs_sentinel_ambient_token"


# Contract: filesystem-layout:Wiring:MUST:5, Auth:MUST:6
@pytest.mark.asyncio
async def test_no_token_branch_drops_ambient_copilot_sdk_auth_token(
    clean_env: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No-token branch MUST NOT forward an ambient COPILOT_SDK_AUTH_TOKEN to the SDK.

    b10 ``client.py:3188-3189`` only sets ``env["COPILOT_SDK_AUTH_TOKEN"]``
    when ``opts.github_token`` is truthy; on the no-token branch the
    provider does not pass ``github_token``, so without scrubbing, any
    parent-shell value survives into the spawned process and authenticates
    against a credential the provider never resolved.

    Contract: filesystem-layout:Wiring:MUST:5, Auth:MUST:6
    """
    # Strip every var _resolve_token() reads so the no-token branch is taken.
    for k in (
        "GITHUB_TOKEN",
        "COPILOT_AGENT_TOKEN",
        "COPILOT_GITHUB_TOKEN",
        "GH_TOKEN",
    ):
        clean_env.delenv(k, raising=False)
    # The ambient hostile value the SDK would otherwise inherit.
    clean_env.setenv("COPILOT_SDK_AUTH_TOKEN", "ghs_ambient_must_not_leak")
    clean_env.setenv(ENV_VAR_NAME, str(tmp_path / "no-token-home"))

    FakeClient, constructor_calls = _stub_copilot_client()

    with patch(
        "amplifier_module_provider_github_copilot.sdk_adapter._imports.CopilotClient",
        FakeClient,
    ):
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        w = CopilotClientWrapper()
        try:
            await w._ensure_client_initialized("test-no-token-ambient-auth")
        except Exception:
            pass

    assert constructor_calls, "CopilotClient must be constructed on no-token branch"
    kwargs = constructor_calls[0]
    assert kwargs["github_token"] is None, (
        "No-token branch precondition: github_token kwarg must be unset/None"
    )
    assert "COPILOT_SDK_AUTH_TOKEN" not in kwargs["env"], (
        "Auth:MUST:6 — ambient COPILOT_SDK_AUTH_TOKEN must be scrubbed before "
        "the spawned SDK subprocess inherits it"
    )
