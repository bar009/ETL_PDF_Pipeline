"""The uniform provider result interface (systemic plan WS7).

Every provider call returns a ``ProviderResult`` — structured, non-throwing,
and testable. Gemini is the first provider, but consumers depend on this
shape, not on Gemini:

- ``text`` / ``payload`` — the answer (text mode / JSON mode)
- ``provider`` / ``model`` / ``transport`` — where the answer came from
- ``usage_metadata`` / ``duration_seconds`` — what it cost
- ``error_kind`` / ``error_message`` — classified failure, when not ok
- ``raw_evidence_path`` — optional pointer to saved raw evidence

Legacy callers that prefer exceptions use ``raise_for_error()``, which
re-raises the original exception so existing retry/skip logic keeps working.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

ERROR_KINDS = (
    "dependency",        # provider SDK / package missing
    "auth",              # missing or rejected credentials
    "rate_limit",        # quota or throttling
    "transport",         # network, timeout, HTTP-level failure
    "empty_response",    # provider answered with nothing usable
    "malformed_payload", # provider answered, but not in the requested shape
    "unknown",
)


class ProviderError(RuntimeError):
    """Base class for provider failures; carries a classified ``error_kind``."""

    error_kind = "unknown"


def classify_error_kind(exc: BaseException) -> str:
    explicit = getattr(exc, "error_kind", None)
    if explicit in ERROR_KINDS:
        return explicit

    message = str(exc).lower()
    if "google-genai package" in message or "no module named" in message:
        return "dependency"
    if "api key" in message or "unauthorized" in message or "http 401" in message or "http 403" in message:
        return "auth"
    if "http 429" in message or "quota" in message or "rate limit" in message:
        return "rate_limit"
    if "network error" in message or "timed out" in message or "timeout" in message or "http 5" in message:
        return "transport"
    if "empty" in message:
        return "empty_response"
    if "invalid json" in message or "malformed" in message:
        return "malformed_payload"
    return "unknown"


@dataclass
class ProviderResult:
    provider: str
    model: str
    transport: str | None = None
    text: str | None = None
    payload: dict[str, Any] | None = None
    usage_metadata: str | None = None
    duration_seconds: float = 0.0
    error_kind: str | None = None
    error_message: str | None = None
    raw_evidence_path: str | None = None
    # Original exception, kept so legacy callers can re-raise the exact type
    # their retry/skip logic already matches on. Never serialized.
    exception: BaseException | None = field(default=None, repr=False, compare=False)

    @property
    def ok(self) -> bool:
        return self.error_kind is None

    def raise_for_error(self) -> "ProviderResult":
        if self.exception is not None:
            raise self.exception
        if self.error_kind is not None:
            error = ProviderError(self.error_message or "provider call failed")
            error.error_kind = self.error_kind
            raise error
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "transport": self.transport,
            "text": self.text,
            "payload": self.payload,
            "usage_metadata": self.usage_metadata,
            "duration_seconds": self.duration_seconds,
            "error_kind": self.error_kind,
            "error_message": self.error_message,
            "raw_evidence_path": self.raw_evidence_path,
            "ok": self.ok,
        }


class _Timer:
    def __enter__(self) -> "_Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.elapsed = round(time.perf_counter() - self._start, 6)


def timed() -> _Timer:
    return _Timer()
