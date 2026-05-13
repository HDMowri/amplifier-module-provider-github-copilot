# Contract: Provider Protocol

## Version
- **Current:** 1.2 (v2.1 Kernel-Validated)
- **Module Reference:** amplifier_module_provider_github_copilot/provider.py
- **Amplifier Contract:** amplifier-core PROVIDER_CONTRACT.md
- **Status:** Specification
- **Updated:** 2026-05-12 — Added MUST:11 (reasoning_effort plumbing) and QualityGates section. Cross-referenced `observability:Events:MUST:6` (pre-flight ConfigurationError exempt from llm:request/llm:response emission).

---

## Overview

This contract defines the **4 methods + 1 property** Provider Protocol that our provider MUST implement to integrate with Amplifier's orchestrator. The provider is a thin orchestrator that delegates to specialized modules.

---

## Module Entry Point

### mount()

```python
from amplifier_core import ModuleCoordinator

async def mount(
    coordinator: ModuleCoordinator,
    config: dict[str, Any] | None = None,
) -> CleanupFn | None: ...
```

**Behavioral Requirements:**
- **MUST** accept `ModuleCoordinator` as first argument (type-safe)
- **MUST** return cleanup callable on success
- **MUST** raise exception on failure (framework must distinguish failure from opt-out)
- **MUST** register provider with coordinator via `coordinator.mount()`
- **MUST** use process-level singleton for SDK client (memory efficiency)

**Failure Semantics:**
- Returning `None` indicates "provider chose not to load" (opt-out)
- Raising an exception indicates "provider failed to load" (error)
- **RATIONALE:** Framework needs to distinguish between a provider that doesn't apply vs one that's broken

**Type Conformance:**
- **MUST** use `ModuleCoordinator` instead of `Any` for type safety
- **RATIONALE:** Ecosystem providers (anthropic, openai, azure-openai) use typed coordinator

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:mount:MUST:1` | Accepts ModuleCoordinator type |
| `provider-protocol:mount:MUST:2` | Returns cleanup callable |
| `provider-protocol:mount:MUST:3` | Registers provider on coordinator |
| `provider-protocol:mount:MUST:5` | Uses process-level singleton for SDK client |

---

## The Protocol (4 Methods + 1 Property)

### 1. name (property)

```python
@property
def name(self) -> str: ...
```

**Behavioral Requirements:**
- **MUST** return `"github-copilot"` (exact string)
- **MUST** be a property, not a method call
- **MUST NOT** vary based on configuration

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:name:MUST:1` | Returns "github-copilot" |
| `provider-protocol:name:MUST:2` | Is a property |

---

### 2. get_info()

```python
def get_info(self) -> ProviderInfo: ...
```

**Behavioral Requirements:**
- **MUST** return `ProviderInfo` with accurate metadata
- **MUST** include `defaults.context_window` for budget calculation
- **MUST** include `config_fields` for init wizard integration
- **SHOULD** cache model info to avoid repeated API calls
- **MAY** include additional provider-specific metadata

**ConfigField Requirements:**
- **MUST** include ConfigField for GitHub token (`env_var="GITHUB_TOKEN"`)
- **MUST** use `field_type="secret"` for token fields
- **RATIONALE:** Init wizard uses config_fields to prompt user for credentials

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:get_info:MUST:1` | Returns valid ProviderInfo |
| `provider-protocol:get_info:MUST:2` | Includes context_window |
| `provider-protocol:get_info:MUST:3` | Includes config_fields with token field |

---

### 3. list_models()

```python
async def list_models(self) -> list[ModelInfo]: ...
```

**Behavioral Requirements:**
- **MUST** return all available models from SDK
- **MUST** include `context_window` and `max_output_tokens` per model
- **SHOULD** cache results for session lifetime
- **MUST** translate SDK model info to `ModelInfo` domain type

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:list_models:MUST:1` | Returns model list |
| `provider-protocol:list_models:MUST:2` | Includes context_window |

---

### 4. complete()

```python
async def complete(
    self,
    request: ChatRequest,
    **kwargs,
) -> ChatResponse: ...
```

**Note:** The kernel passes `**kwargs` for extensibility. Internal streaming callbacks are provider-internal, not part of the protocol.

**Behavioral Requirements:**
- **MUST** create ephemeral session per call (per deny-destroy.md)
- **MUST** forward `ChatRequest.tools` to SDK session (per sdk-boundary.md Tool Forwarding Contract)
- **MUST** extract and forward images from `ChatRequest.messages` (per sdk-boundary.md Image Passthrough)
- **MUST** capture tool calls (NOT execute them)
- **MUST** destroy session after first turn completes
- **MUST NOT** maintain state between calls
- **MUST** translate SDK errors to kernel errors (per error-hierarchy.md)
- **MUST** forward `ChatRequest.max_output_tokens` (when not None) to the SDK as a
  per-session output token cap by passing
  `model_capabilities=ModelCapabilitiesOverride(limits=ModelLimitsOverride(max_output_tokens=<value>))`
  on `create_session()`. This relies on the `model_capabilities` parameter
  introduced in `github-copilot-sdk>=0.3.0`. Note: the canonical kernel field is
  `max_output_tokens` (not `max_tokens`) — confirmed by amplifier-core proto field 6,
  `message_models.ChatRequest`, and the Anthropic/OpenAI provider implementations.
- **MUST** forward `ChatRequest.reasoning_effort` (when not None and not the
  empty string) to the SDK as the `reasoning_effort` kwarg on `client.session()`,
  which the SDK adapter translates to
  `CopilotClient.create_session(reasoning_effort=<value>)` and the SDK
  serializes onto the JSON-RPC `session.create` payload as `reasoningEffort`.
  Before the SDK call, the provider MUST pre-validate the value against the
  resolved model's capability descriptor: if
  `CopilotModelInfo.supports_reasoning_effort` is False, or the value is not in
  `CopilotModelInfo.supported_reasoning_efforts` (when that allowlist is
  non-empty), raise `kernel_errors.ConfigurationError` with the offending
  model id, the rejected value, and (when applicable) the allowed set. The
  empty string `""` is treated as None (no effort requested). Forwarding
  applies to BOTH the normal completion call site and the fake-tool correction
  retry call site in `provider.py`. Relies on `github-copilot-sdk>=0.3.0`
  (`create_session(reasoning_effort=...)` — signature at `client.py:1198`,
  payload write at `client.py:1322`).

**Session Lifecycle:**
```
complete() called
    │
    ├─→ Create ephemeral session (with deny hook + tool definitions)
    │
    ├─→ Extract images from last user message (as BlobAttachments)
    │
    ├─→ Send prompt with attachments, capture response
    │
    ├─→ Capture tool calls (not execute)
    │
    └─→ Destroy session, return response
```

**Enforcement Disclaimer for `max_output_tokens` (MUST:10):**

The provider's MUST:10 obligation is **forwarding**, not **enforcement**. The
distinction is rooted in three layers, each verified against the live SDK and
real-world model behavior:

1. **Provider** — serializes
   `model_capabilities=ModelCapabilitiesOverride(limits=ModelLimitsOverride(max_output_tokens=N))`
   onto `create_session()`. Verified by
   `tests/test_truncation_visibility.py::TestSessionForwardsMaxTokens`.
2. **SDK** (`copilot.client._capabilities_to_dict`) — writes the value into the
   JSON-RPC payload as `modelCapabilities.limits.max_output_tokens` and ships
   it to the headless `copilot` binary. The SDK contains **no enforcement
   logic**; the docstring on `create_session` describes the parameter as
   `"Override individual model capabilities resolved by the runtime"`.
3. **Backend / model runtime** — may or may not honor the cap, per model. Live
   evidence (April 2026, github-copilot-sdk 0.3.0): with `max_output_tokens=30`
   and a controlled counting prompt, `claude-sonnet-4.5` and `claude-haiku-4.5`
   both produced **>1000 output tokens** with `finish_reason="stop"`.

**Caller obligations:**

- Callers **MUST NOT** treat `max_output_tokens` as a hard cost cap. Treat it as
  a hint that some model runtimes honor and others ignore.
- When the cap **is** enforced by a backend, the provider surfaces the signal
  via `finish_reason="length"` and a single WARNING log line per
  `streaming-contract:FinishReason:MUST:6`. Callers wanting deterministic
  output budgeting must implement post-response truncation themselves.

**Provider obligations under MUST:10 are unchanged:** forward when not None;
do not raise. The provider is correct as long as the value reaches the SDK
`create_session(model_capabilities=...)` call; what the runtime does with it
is out of contract scope.

This pattern matches `amplifier-module-provider-anthropic` (forwards
`request.max_output_tokens` to the Anthropic SDK with no clamp or enforcement)
and the kernel field definition itself
(`amplifier_core.message_models.ChatRequest.max_output_tokens: int | None = None`,
no enforcement docstring).

**Enforcement Disclaimer for `reasoning_effort` (MUST:11):**

The provider's MUST:11 obligation is **forward + pre-validate**, not enforce
that the model actually reasons. Three layers are in scope:

1. **Provider Layer 1 (proactive gate)** — `validate_reasoning_effort()` in
   `request_adapter.py` is called from `provider.complete()` after
   `convert_chat_request` and after `CopilotModelInfo` lookup. Raises
   `kernel_errors.ConfigurationError` on (a) `supports_reasoning_effort=False`,
   (b) value outside a non-empty `supported_reasoning_efforts` allowlist,
   (c) value longer than 16 chars (defensive), (d) mixed-case value (SDK is
   strictly lowercase Literal), or (e) cache-miss (`model_info is None`)
   AND value not in the SDK literal allowlist
   `{"low","medium","high","xhigh"}` mirroring the SDK's
   `ReasoningEffort` Literal. Verified by `tests/test_reasoning_effort.py`.
2. **Provider Layer 2 (SDK-error backstop)** — when Layer 1 is bypassed
   (stale capability cache, model added server-side, or model_info lookup
   miss), the SDK raises `JsonRpcError` with `"does not support"` text.
   `errors.yaml:P4` substring rule maps this to `ConfigurationError` via
   `error_translation.py`. Layer-1 and Layer-2 raise the SAME class —
   contract obligation, not coincidence.
3. **Backend / model runtime** — decides whether to actually allocate
   reasoning tokens. `claude-opus-4.7` family advertises
   `supports_reasoning_effort=True` yet may emit zero `assistant.reasoning*`
   events (filed upstream as F3-B); `claude-haiku-4.5` may emit reasoning
   despite advertising `=False`. The provider does not police runtime
   behavior.

**Caller obligations:**

- Callers MUST treat a successful forward as "the value reached the runtime,"
  NOT as "the model will reason at this depth."
- Callers MUST NOT rely on `assistant.reasoning*` events being emitted for any
  given (model, effort) pair; the runtime decides.
- Empty string `""` is treated as None (no effort requested).
- Mixed-case values (e.g., `"Medium"`) are rejected; SDK contract is strictly
  lowercase per `Literal["low","medium","high","xhigh"]`.

**Provider obligations under MUST:11:** when not None and not empty, validate
against the target model's capability descriptor and forward the verbatim
string to `client.session(reasoning_effort=...)`; both the main completion
path and the fake-tool correction retry path MUST forward identically.
`_execute_sdk_completion` MUST accept `reasoning_effort` as an explicit
keyword argument (no `**kwargs` smuggle).

**Module References (MUST:11):**
- Layer-1 gate: `request_adapter.validate_reasoning_effort`
- Provider call site: `provider.GitHubCopilotProvider.complete` (pre-SDK
  capability gate) and `provider.GitHubCopilotProvider._execute_sdk_completion`
  (explicit `reasoning_effort` parameter; both main and fake-tool-retry paths)
- Membrane forward: `sdk_adapter.client.CopilotClientWrapper.session`
  (forwards `reasoning_effort` to `CopilotClient.create_session`)
- Carrier field: `sdk_adapter.types.CompletionRequest.reasoning_effort`
- Capability descriptor: `sdk_adapter.CopilotModelInfo.supports_reasoning_effort`
  and `supported_reasoning_efforts`
- Layer-2 backstop: `config/data/errors.yaml` rule P4 → `error_translation.py`

This pattern parallels MUST:10 (forward-not-enforce). The sibling Anthropic
provider's pattern is **forwarding-only** (`getattr(request, "reasoning_effort",
None)` straight into the Anthropic SDK call without a capability gate); this
provider adds the Layer-1 capability gate because the GitHub Copilot SDK
exposes per-model capability metadata (`CopilotModelInfo`) that the Anthropic
provider does not have, and because a server-side rejection here surfaces as a
remote `JsonRpcError` rather than a local TypeError. Layer 1 keeps the failure
local and gives a helpful error enumerating the accepted values.

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:complete:MUST:1` | Creates ephemeral session |
| `provider-protocol:complete:MUST:2` | Forwards tools to SDK session |
| `provider-protocol:complete:MUST:3` | Captures tool calls |
| `provider-protocol:complete:MUST:4` | Destroys session after turn |
| `provider-protocol:complete:MUST:5` | No state between calls |
| `provider-protocol:complete:MUST:6` | Detects fake tool calls and retries with correction |
| `provider-protocol:complete:MUST:7` | Extracts images from last user message |
| `provider-protocol:complete:MUST:8` | Forwards images as BlobAttachments to SDK |
| `provider-protocol:complete:MUST:9` | When malformed tool sequences are detected (tool call without matching tool result in current request), MUST insert synthetic tool-result messages before prompt extraction and MUST log one WARNING per repair event; MUST NOT raise |
| `provider-protocol:complete:MUST:10` | When `ChatRequest.max_output_tokens` is not None, MUST forward it to SDK `create_session()` as `model_capabilities=ModelCapabilitiesOverride(limits=ModelLimitsOverride(max_output_tokens=<value>))`; MUST NOT raise; relies on `github-copilot-sdk>=0.3.0` |
| `provider-protocol:complete:MUST:11` | When `ChatRequest.reasoning_effort` is not None and not empty, MUST pre-validate the value against the SDK literal allowlist `{"low","medium","high","xhigh"}` (case-sensitive) regardless of cache state, then against the resolved model's `supports_reasoning_effort` and `supported_reasoning_efforts`; on cache-miss (`CopilotModelInfo` unavailable) MUST emit an INFO log deferring final per-model validation to the SDK Layer-2 backstop; on any mismatch MUST raise `kernel_errors.ConfigurationError` before any SDK call; otherwise MUST forward verbatim to `client.session(reasoning_effort=<value>)` on BOTH the main and fake-tool-retry call sites; relies on `github-copilot-sdk>=0.3.0` |

---

### 5. parse_tool_calls()

```python
def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...
```

**Note:** Returns `list[ToolCall]`, NOT `list[ToolCallBlock]`. `ToolCall` has `arguments`, not `input`.

**Behavioral Requirements:**
- **MUST** extract tool calls from response
- **MUST** return empty list if no tool calls
- **MUST NOT** execute tools (orchestrator responsibility)
- **MUST** preserve tool call IDs for result correlation
- **MUST** be synchronous — callers MUST NOT await the return value

**Synchronous Contract:**

`parse_tool_calls` is defined as a plain function (not a coroutine) at every
layer of the Amplifier stack. This is not a convention — it is a hard requirement
imposed by the kernel bridges that call this method without `await`:

- **Python Protocol** (`amplifier_core/interfaces.py`, class `Provider(Protocol)`):
  `def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]`
- **Rust trait** (`amplifier-core/crates/amplifier-core/src/traits.rs:188`):
  `fn parse_tool_calls(&self, response: &ChatResponse) -> Vec<ToolCall>`
- **WASM bridge** (`amplifier-core/crates/amplifier-core/src/bridges/wasm_provider.rs:255`):
  inline comment — *"Call WASM synchronously. parse_tool_calls is not async in the trait"*
- **gRPC bridge** (`amplifier-core/crates/amplifier-core/src/bridges/grpc_provider.rs:174`):
  `fn parse_tool_calls(&self, response: &ChatResponse) -> Vec<ToolCall>`

**Consequence of violation:** An `async def` implementation returns a coroutine
object. Python coroutines are truthy — the kernel's tool-dispatch loop would
interpret every response as having tool calls regardless of actual content. This
failure is silent: no exception is raised, no type error, no warning. The kernel
enters an infinite dispatch loop on ordinary text responses.

**ToolCall Structure:**
```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]  # NOT "input"
```

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:parse_tool_calls:MUST:1` | Extracts tool calls |
| `provider-protocol:parse_tool_calls:MUST:2` | Returns empty list when none |
| `provider-protocol:parse_tool_calls:MUST:3` | Preserves tool call IDs |
| `provider-protocol:parse_tool_calls:MUST:4` | Uses arguments, not input |
| `provider-protocol:parse_tool_calls:MUST:5` | Is synchronous — callers must not await |

---

## Observability Hooks

### Hook Emission Requirements

Providers **MUST** emit observability events to `coordinator.hooks.emit()` for integration with Amplifier's monitoring infrastructure.

**Evidence:** All canonical providers (anthropic, openai, azure-openai) emit these hooks.

### Required Events

#### llm:request

**MUST** emit before SDK API call with request metadata.

```python
await self._emit_event("llm:request", {
    "provider": self.name,
    "model": model,
    "message_count": len(messages),
    "tool_count": len(tools) if tools else 0,
    "streaming": use_streaming,
    "timeout": timeout,
    # Optional: "raw": redact_secrets(raw_payload) for debug
})
```

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:hooks:llm_request:MUST:1` | Emits before SDK call |
| `provider-protocol:hooks:llm_request:MUST:2` | Includes provider, model, message_count |

#### llm:response

**MUST** emit after SDK response with status and timing.

```python
# Success
await self._emit_event("llm:response", {
    "provider": self.name,
    "model": model,
    "status": "ok",
    "duration_ms": elapsed_ms,
    "usage": {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    },
    # Per amplifier-core proto: "stop", "tool_calls", "length", "content_filter"
    # Not "end_turn" which is an SDK-specific input value
    "finish_reason": response.finish_reason or "stop",
    "tool_calls": len(response.tool_calls) if response.tool_calls else 0,
})

# Error
await self._emit_event("llm:response", {
    "provider": self.name,
    "model": model,
    "status": "error",
    "duration_ms": elapsed_ms,
    "error_type": type(error).__name__,
    "error_message": str(error),
})
```

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:hooks:llm_response:MUST:1` | Emits after SDK response |
| `provider-protocol:hooks:llm_response:MUST:2` | Includes duration_ms timing |
| `provider-protocol:hooks:llm_response:MUST:3` | Uses status "ok" or "error" |

#### PROVIDER_RETRY (provider:retry)

**MUST** emit before retry sleep when retrying failed requests.

```python
from amplifier_core.events import PROVIDER_RETRY

await self._emit_event(PROVIDER_RETRY, {
    "provider": self.name,
    "model": model,
    "attempt": attempt,
    "max_retries": max_retries,
    "delay": delay_seconds,
    "retry_after": retry_after,   # float seconds from Retry-After header, or None
    "error_type": type(error).__name__,
    "error_message": str(error),  # sanitized via redact_sensitive_text()
})
```

**Payload field types:**
| Field | Type | Notes |
|-------|------|-------|
| `provider` | `str` | Always `"github-copilot"` |
| `model` | `str` | Model ID passed to complete() |
| `attempt` | `int` | 1-based retry count |
| `max_retries` | `int` | From RetryPolicy.max_attempts |
| `delay` | `float` | Seconds sleep will block |
| `retry_after` | `float \| None` | Server Retry-After value; `None` if not present |
| `error_type` | `str` | Kernel error class name |
| `error_message` | `str` | Sanitized via `redact_sensitive_text()` |

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:hooks:provider_retry:MUST:1` | Emits before retry sleep |
| `provider-protocol:hooks:provider_retry:MUST:2` | Includes attempt, max_retries, delay, error_type |
| `provider-protocol:hooks:provider_retry:MUST:3` | Includes retry_after (float or None) — never absent |

### Event Ordering Contract

- **MUST** emit `llm:request` BEFORE `llm:response`
- **MUST** emit `PROVIDER_RETRY` between `llm:request` and next retry attempt

### Graceful Degradation

- **MUST** handle missing coordinator gracefully (no raise)
- **MUST** catch and log hook emission errors (no raise)

The real hook emission mechanism is the `llm_lifecycle` async context manager in `observability.py`,
not a `_emit_event()` method. The context manager handles request, response, and retry hooks
as a unit, ensuring the response hook always fires even on error paths.

```python
# Real pattern — observability.py llm_lifecycle context manager
from .observability import llm_lifecycle

async with llm_lifecycle(coordinator, model) as ctx:
    await ctx.emit_request(request_payload)
    response = await sdk_call(...)
    await ctx.emit_response(response)
# llm_lifecycle emits llm:response on exit even if exception raised
```

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:hooks:emit:MUST:1` | No raise on missing coordinator |
| `provider-protocol:hooks:emit:MUST:2` | No raise on hook errors |

---

## Cross-References

- **deny-destroy.md** — Session ephemerality and deny hook requirements
- **error-hierarchy.md** — Exception translation requirements (kernel types)
- **amplifier-core PROVIDER_CONTRACT.md** — Kernel interface specification

---

## Quality Gates

**MUST** constraints for release readiness:

| Gate | Command | Requirement |
|------|---------|-------------|
| Main package lint | `ruff check amplifier_module_provider_github_copilot/` | 0 errors |
| Main package types | `pyright amplifier_module_provider_github_copilot/` | 0 errors |
| **Test file types** | `pyright tests/` | **0 errors** |
| Full repo types | `pyright .` | 0 errors |
| All tests pass | `pytest tests/ -v` | 0 failures |

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:QualityGates:MUST:1` | Test files must be type-clean (zero pyright errors) |
| `provider-protocol:QualityGates:MUST:2` | Full-repo `pyright .` must pass before release |

**Rationale:** Running pyright only on the main package allowed test file errors to accumulate undetected. Test files are part of the deliverable and must be type-clean for Microsoft OSS release.

---

## Public API Surface

### __all__ Export List

The module's `__all__` defines the stable public API.

**Behavioral Requirements:**
- **MUST** export only `mount` and the provider class
- **MUST NOT** re-export kernel types (`ModelInfo`, `ProviderInfo`)
- **MUST** match ecosystem convention (anthropic, openai, azure-openai)

**Rationale:** Kernel types belong to `amplifier_core`. Re-exporting them couples the provider's API to kernel internals and creates version skew risks.

**Canonical Pattern:**
```python
__all__ = ["mount", "GitHubCopilotProvider"]
```

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:public_api:MUST:1` | Exports only mount and provider class |
| `provider-protocol:public_api:MUST:2` | Does not re-export kernel types |

---

## Implementation Checklist

- [ ] `mount()` accepts `ModuleCoordinator` type (not `Any`)
- [ ] `mount()` returns cleanup callable
- [ ] `name` property returns "github-copilot"
- [ ] `get_info()` returns valid ProviderInfo
- [ ] `get_info()` includes config_fields with GitHub token field
- [ ] `list_models()` queries SDK and caches
- [ ] `complete()` accepts `**kwargs` (not named callback)
- [ ] `complete()` creates ephemeral session with deny hook
- [ ] `complete()` forwards tools to SDK session (per sdk-boundary.md ToolForwarding:MUST:1)
- [ ] `complete()` captures and returns tool calls
- [ ] `parse_tool_calls()` returns `list[ToolCall]`
- [ ] `parse_tool_calls()` uses `arguments` field
- [ ] All SDK errors translated to kernel types
- [ ] **Test files pass `pyright tests/` with 0 errors**
- [ ] `complete()` emits `llm:request` before SDK call
- [ ] `complete()` emits `llm:response` after completion (success or error)
- [ ] Retry loop emits `PROVIDER_RETRY` before sleep
- [ ] `llm_lifecycle` context manager handles missing coordinator gracefully
