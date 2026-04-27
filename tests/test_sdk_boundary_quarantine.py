"""SDK boundary quarantine tests.

Contract: contracts/sdk-boundary.md

Tests in this module verify:
- ImportQuarantine:MUST:1 — SDK imports confined to sdk_adapter/
- ImportQuarantine:MUST:5 — ImportError with install instructions if SDK absent
- ImportQuarantine:MUST:6 — Direct imports for pinned SDK version (no fallback chains)
- ImportQuarantine:MUST:7 — SDK constructor calls encapsulated via factory
- Membrane:MUST:1 — Import from sdk_adapter package, not submodules
- Membrane:MUST:3 — __init__.py does not expose _imports module
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from types import ModuleType

# Root path for source code
SDK_ADAPTER_PATH = Path("amplifier_module_provider_github_copilot/sdk_adapter")
IMPORTS_FILE = SDK_ADAPTER_PATH / "_imports.py"


class TestSDKImportQuarantine:
    """Verify SDK imports are quarantined in _imports.py.

    Contract: sdk-boundary:Membrane:MUST:1
    """

    def test_imports_py_exists(self) -> None:
        """_imports.py MUST exist as the single SDK import point.

        Contract: sdk-boundary:Membrane:MUST:1
        """
        # Contract: sdk-boundary:Membrane:MUST:1
        assert IMPORTS_FILE.exists(), (
            f"_imports.py not found at {IMPORTS_FILE}. "
            "SDK imports must be quarantined in _imports.py."
        )


class TestSDKAdapterExports:
    """Verify __init__.py does not expose private quarantine module.

    Contract: sdk-boundary:Membrane:MUST:3
    """

    def test_init_does_not_expose_imports_module(self) -> None:
        """__init__.py MUST NOT re-export the _imports quarantine module.

        Contract: sdk-boundary:Membrane:MUST:3

        Domain code must use the public sdk_adapter API, never reach into
        _imports directly. If _imports is in __all__, domain code could
        accidentally bypass the membrane.
        """
        # Contract: sdk-boundary:Membrane:MUST:3
        init_file = SDK_ADAPTER_PATH / "__init__.py"
        assert init_file.exists(), f"{init_file} must exist in the repository"

        content = init_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        # Find __all__ list and check it does not contain "_imports"
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            exports = [
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                            ]
                            assert "_imports" not in exports, (
                                "__all__ exports '_imports' — this violates "
                                "sdk-boundary:Membrane:MUST:3. Domain code must not "
                                "reach into private quarantine module."
                            )


class TestSDKImportsRealPath:
    """Cover sdk_adapter/_imports.py real SDK import paths.

    Contract: sdk-boundary:Membrane:MUST:5
    Contract: sdk-boundary:ImportQuarantine:MUST:6
    """

    def _save_import_state(self) -> tuple[str | None, ModuleType | None]:
        """Save environment and module state before import tests."""
        original_skip = os.environ.get("SKIP_SDK_CHECK")
        original_module = sys.modules.pop(
            "amplifier_module_provider_github_copilot.sdk_adapter._imports", None
        )
        return original_skip, original_module

    def _restore_import_state(
        self, original_skip: str | None, original_module: ModuleType | None
    ) -> None:
        """Restore environment and module state after import tests."""
        if original_skip is not None:
            os.environ["SKIP_SDK_CHECK"] = original_skip
        else:
            os.environ["SKIP_SDK_CHECK"] = "1"

        sys.modules.pop("amplifier_module_provider_github_copilot.sdk_adapter._imports", None)

        if original_module is not None:
            sys.modules["amplifier_module_provider_github_copilot.sdk_adapter._imports"] = (
                original_module
            )

    def test_sdk_import_failure_raises_import_error(self) -> None:
        """copilot import failing MUST raise ImportError with install instructions.

        Contract: sdk-boundary:Membrane:MUST:5

        When SKIP_SDK_CHECK is not set and copilot is not importable,
        _imports.py must raise ImportError with a message containing
        'github-copilot-sdk not installed'.
        """
        # Contract: sdk-boundary:Membrane:MUST:5
        original_skip, original_module = self._save_import_state()

        try:
            os.environ.pop("SKIP_SDK_CHECK", None)

            # Clear any cached copilot modules
            copilot_modules = [k for k in sys.modules if k.startswith("copilot")]
            for k in copilot_modules:
                sys.modules.pop(k, None)

            with patch.dict("sys.modules", {"copilot": None}):
                with pytest.raises(ImportError, match="github-copilot-sdk not installed"):
                    importlib.import_module(
                        "amplifier_module_provider_github_copilot.sdk_adapter._imports"
                    )
        finally:
            self._restore_import_state(original_skip, original_module)

    def test_permission_request_result_loads_from_copilot_session(self) -> None:
        """PermissionRequestResult MUST resolve directly from copilot.session.

        Contract: sdk-boundary:ImportQuarantine:MUST:6

        SDK v0.3.0 canonical location: copilot.session.
        Direct import — no fallback chain.
        """
        # Contract: sdk-boundary:ImportQuarantine:MUST:6
        original_skip, original_module = self._save_import_state()

        try:
            os.environ.pop("SKIP_SDK_CHECK", None)

            mock_prr = MagicMock(name="PermissionRequestResult")
            mock_copilot = MagicMock(spec=["CopilotClient", "SubprocessConfig"])
            mock_copilot.CopilotClient = MagicMock(name="CopilotClient")
            mock_copilot.SubprocessConfig = MagicMock(name="SubprocessConfig")

            mock_copilot_session = MagicMock(spec=["PermissionRequestResult"])
            mock_copilot_session.PermissionRequestResult = mock_prr

            with patch.dict(
                "sys.modules",
                {
                    "copilot": mock_copilot,
                    "copilot.session": mock_copilot_session,
                },
            ):
                mod = importlib.import_module(
                    "amplifier_module_provider_github_copilot.sdk_adapter._imports"
                )

            assert mod.PermissionRequestResult is mock_prr, (
                f"PermissionRequestResult is {mod.PermissionRequestResult!r} but should be "
                f"{mock_prr!r}. _imports.py must import directly from copilot.session."
            )

        finally:
            self._restore_import_state(original_skip, original_module)

    def test_subprocess_config_loads_from_copilot_root(self) -> None:
        """SubprocessConfig MUST resolve directly from copilot root.

        Contract: sdk-boundary:ImportQuarantine:MUST:6

        SDK v0.3.0 canonical location: copilot root (re-exported from copilot.client).
        Direct import — no fallback chain.
        """
        # Contract: sdk-boundary:ImportQuarantine:MUST:6
        original_skip, original_module = self._save_import_state()

        try:
            os.environ.pop("SKIP_SDK_CHECK", None)

            mock_subprocess_config = MagicMock(name="SubprocessConfig")
            mock_copilot = MagicMock(spec=["CopilotClient", "SubprocessConfig"])
            mock_copilot.CopilotClient = MagicMock(name="CopilotClient")
            mock_copilot.SubprocessConfig = mock_subprocess_config

            mock_copilot_session = MagicMock(spec=["PermissionRequestResult"])
            mock_copilot_session.PermissionRequestResult = MagicMock(name="PermissionRequestResult")

            with patch.dict(
                "sys.modules",
                {
                    "copilot": mock_copilot,
                    "copilot.session": mock_copilot_session,
                },
            ):
                mod = importlib.import_module(
                    "amplifier_module_provider_github_copilot.sdk_adapter._imports"
                )

            assert mod.SubprocessConfig is mock_subprocess_config, (
                f"SubprocessConfig is {mod.SubprocessConfig!r} but should be "
                f"{mock_subprocess_config!r}. _imports.py must import directly from copilot root."
            )

        finally:
            self._restore_import_state(original_skip, original_module)


class TestSDKConstructorEncapsulation:
    """Verify SDK constructor calls are encapsulated in _imports.py.

    Contract: sdk-boundary:ImportQuarantine:MUST:7
    """

    def test_make_permission_denied_exists_in_imports(self) -> None:
        """_imports.py MUST expose make_permission_denied factory.

        Contract: sdk-boundary:ImportQuarantine:MUST:7

        The factory encapsulates SDK constructor field knowledge so
        that client.py expresses intent only.
        """
        # Contract: sdk-boundary:ImportQuarantine:MUST:7
        content = IMPORTS_FILE.read_text(encoding="utf-8")
        tree = ast.parse(content)

        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "make_permission_denied" in function_names, (
            "ImportQuarantine:MUST:7 — _imports.py must define make_permission_denied factory"
        )

    def test_make_permission_denied_returns_reject(self) -> None:
        """make_permission_denied MUST return result with kind='reject'.

        Contract: sdk-boundary:ImportQuarantine:MUST:7

        In test mode (SKIP_SDK_CHECK=1), PermissionRequestResult is None
        and the factory returns a dict. Verify exact field value.
        """
        # Contract: sdk-boundary:ImportQuarantine:MUST:7
        from amplifier_module_provider_github_copilot.sdk_adapter._imports import (
            make_permission_denied,
        )

        result = make_permission_denied()

        # Handle both real SDK object and dict fallback
        kind = result.kind if hasattr(result, "kind") else result.get("kind")
        assert kind == "reject", (
            f"ImportQuarantine:MUST:7 — make_permission_denied must return kind='reject', "
            f"got {kind!r}"
        )
        assert isinstance(kind, str), (
            f"ImportQuarantine:MUST:7 — kind must be str, got {type(kind).__name__}"
        )

    def test_client_does_not_call_permission_constructor_directly(self) -> None:
        """client.py MUST NOT call PermissionRequestResult(...) directly.

        Contract: sdk-boundary:ImportQuarantine:MUST:7

        SDK constructor calls must be encapsulated in _imports.py via factory.
        client.py must express intent only (call make_permission_denied),
        never instantiate SDK types directly.
        """
        # Contract: sdk-boundary:ImportQuarantine:MUST:7
        client_file = SDK_ADAPTER_PATH / "client.py"
        assert client_file.exists(), f"{client_file} must exist in the repository"

        content = client_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for direct PermissionRequestResult(...) calls
                if isinstance(node.func, ast.Name) and node.func.id == "PermissionRequestResult":
                    violations.append(
                        f"PermissionRequestResult(...) called directly at line {node.lineno}"
                    )
                elif (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "PermissionRequestResult"
                ):
                    violations.append(
                        f"*.PermissionRequestResult(...) called directly at line {node.lineno}"
                    )

        assert violations == [], (
            "client.py calls SDK constructor directly — violates "
            "sdk-boundary:ImportQuarantine:MUST:7:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nFix: use make_permission_denied() factory from _imports.py"
        )

    def test_make_permission_denied_uses_only_kind_kwarg(self) -> None:
        """make_permission_denied MUST pass only kind= to PermissionRequestResult constructor.

        Contract: sdk-boundary:ImportQuarantine:MUST:7

        SDK v0.3.0 removed the rules, feedback, message, and path fields from
        PermissionRequestResult. Only kind= must be passed. Any extra kwarg causes
        TypeError at runtime.
        """
        # Contract: sdk-boundary:ImportQuarantine:MUST:7
        content = IMPORTS_FILE.read_text(encoding="utf-8")
        tree = ast.parse(content)

        call_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "make_permission_denied":
                for call_node in ast.walk(node):
                    if (
                        isinstance(call_node, ast.Call)
                        and isinstance(call_node.func, ast.Name)
                        and call_node.func.id == "PermissionRequestResult"
                    ):
                        call_found = True
                        assert len(call_node.args) == 0, (
                            "PermissionRequestResult must be called with keyword-only args — "
                            "no positional args allowed"
                        )
                        kwarg_keys = [kw.arg for kw in call_node.keywords]
                        assert kwarg_keys == ["kind"], (
                            f"PermissionRequestResult must be called with only kind= kwarg, "
                            f"got {kwarg_keys!r}. "
                            "SDK v0.3.0 removed: rules, feedback, message, path fields — "
                            "extra kwargs cause TypeError."
                        )

        assert call_found, (
            "ImportQuarantine:MUST:7 — make_permission_denied must call PermissionRequestResult"
        )


class TestSDKNoFallbackChains:
    """Verify _imports.py has no fallback chains or deleted-module imports.

    Contract: sdk-boundary:ImportQuarantine:MUST:6
    """

    def test_imports_py_has_no_copilot_types_import(self) -> None:
        """_imports.py MUST NOT import from copilot.types.

        Contract: sdk-boundary:ImportQuarantine:MUST:6

        copilot.types was deleted in SDK v0.2.1. Any import from it fails at
        import time with SDK >= v0.2.1. With pin >=0.3.0, this module is always
        absent. Direct imports from canonical locations only — no fallback chains.
        """
        # Contract: sdk-boundary:ImportQuarantine:MUST:6
        content = IMPORTS_FILE.read_text(encoding="utf-8")
        tree = ast.parse(content)

        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "copilot.types":
                names = ", ".join(alias.name for alias in node.names)
                violations.append(f"from copilot.types import {names} at line {node.lineno}")

        assert violations == [], (
            "_imports.py imports from copilot.types (deleted in SDK v0.2.1):\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nFix: use canonical SDK v0.3.0 locations — "
            "PermissionRequestResult: copilot.session | SubprocessConfig: copilot root."
        )


class TestMembraneAPIPattern:
    """Verify domain code uses sdk_adapter package API, not submodule imports.

    Contract: sdk-boundary:Membrane:MUST:1, sdk-boundary:Membrane:MUST:3

    Domain modules (provider.py, streaming.py, request_adapter.py, __init__.py)
    MUST import from .sdk_adapter package, NOT from .sdk_adapter.client,
    .sdk_adapter.types, etc. directly.

    This ensures encapsulation: internal restructuring doesn't break domain code.
    """

    # Domain files that should use membrane API
    DOMAIN_FILES = [
        "amplifier_module_provider_github_copilot/provider.py",
        "amplifier_module_provider_github_copilot/streaming.py",
        "amplifier_module_provider_github_copilot/request_adapter.py",
        "amplifier_module_provider_github_copilot/__init__.py",
    ]

    # Forbidden submodule import patterns (should use .sdk_adapter not .sdk_adapter.X)
    FORBIDDEN_PATTERNS = [
        ".sdk_adapter.client",
        ".sdk_adapter.event_helpers",
        ".sdk_adapter.extract",
        ".sdk_adapter.tool_capture",
        ".sdk_adapter.types",
        ".sdk_adapter._imports",
        ".sdk_adapter._spec_utils",
        ".sdk_adapter.model_translation",
    ]

    @pytest.mark.parametrize("file_path", DOMAIN_FILES)
    def test_domain_file_uses_membrane_api(self, file_path: str) -> None:
        """Domain file MUST import from sdk_adapter package, not submodules.

        Contract: sdk-boundary:Membrane:MUST:1, sdk-boundary:Membrane:MUST:3

        Example of WRONG (bypasses membrane):
            from .sdk_adapter.client import CopilotClientWrapper

        Example of RIGHT (uses membrane):
            from .sdk_adapter import CopilotClientWrapper
        """
        # Contract: sdk-boundary:Membrane:MUST:1, sdk-boundary:Membrane:MUST:3
        py_file = Path(file_path)
        assert py_file.exists(), f"{file_path} must exist in the repository"

        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                # Check if import is from sdk_adapter submodule
                for pattern in self.FORBIDDEN_PATTERNS:
                    if node.module.endswith(pattern) or pattern in node.module:
                        names = ", ".join(alias.name for alias in node.names)
                        violations.append(
                            f"from {node.module} import {names} "
                            f"(line {node.lineno}) — should use from .sdk_adapter import"
                        )

        assert violations == [], (
            f"{file_path} bypasses sdk_adapter membrane:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nFix: import from .sdk_adapter package, not submodules. "
            "See sdk-boundary:Membrane:MUST:1"
        )
