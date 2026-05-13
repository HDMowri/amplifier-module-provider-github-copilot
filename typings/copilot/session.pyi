"""Type stubs for ``copilot.session`` submodule (SDK v0.3.0).

Provider imports ``PermissionRequestResult`` and ``PermissionRequestResultKind``
from here; ``ReasoningEffort`` is also re-exported at this path by the live
SDK (verified via ``dir(copilot.session)`` 2026-05-12) so the stub mirrors
that surface for downstream consumers that prefer the session-module import.

Shape verified against the live SDK v0.3.0 source on 2026-05-12:

* ``PermissionRequestResultKind`` is a Literal of four kinds.
* ``PermissionRequestResult`` is a ``@dataclass`` with a single positional
  field ``kind`` defaulting to ``"user-not-available"``. There is NO
  ``**kwargs`` in the real ``__init__``; declaring one would be more
  permissive than the SDK and mask call-site errors at the boundary.
* ``ReasoningEffort`` is a ``Literal["low","medium","high","xhigh"]``
  re-exported from ``copilot.session`` and ``copilot.client``.
"""

from dataclasses import dataclass
from typing import Literal

PermissionRequestResultKind = Literal[
    "approve-once",
    "reject",
    "user-not-available",
    "no-result",
]


@dataclass
class PermissionRequestResult:
    """SDK v0.3.0 permission-request reply object.

    Constructed by the provider as ``PermissionRequestResult(kind="reject")``
    or with the default ``user-not-available`` value.
    """

    kind: PermissionRequestResultKind = "user-not-available"


ReasoningEffort = Literal["low", "medium", "high", "xhigh"]


__all__ = [
    "PermissionRequestResult",
    "PermissionRequestResultKind",
    "ReasoningEffort",
]
