from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable


RuntimeValidator = Callable[[Any], Any]
RuntimeLogger = Callable[[str], None]


@dataclass(frozen=True)
class ProviderRuntimeClient:
    provider: str
    client: Any
    types: Any


@dataclass
class ModelRequestResult:
    ok: bool
    payload: Any | None
    metadata: dict[str, Any]
    attempt_failures: list[dict[str, Any]]
    failure: dict[str, Any] | None = None
    raw_response_text: str | None = None


class _StructuredRuntimeError(RuntimeError):
    def __init__(
        self,
        *,
        status: str,
        message: str,
        raw_response_text: str | None = None,
        raw_response_present: bool = False,
        json_parse_ok: bool = False,
        json_repaired: bool = False,
        schema_valid: bool = False,
        error_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.raw_response_text = raw_response_text
        self.raw_response_present = raw_response_present
        self.json_parse_ok = json_parse_ok
        self.json_repaired = json_repaired
        self.schema_valid = schema_valid
        self.error_type = error_type or type(self).__name__


def build_provider_runtime(
    *,
    provider: str,
    api_key: str,
    timeout_ms: int,
) -> ProviderRuntimeClient:
    if provider != "gemini":
        raise RuntimeError(f"Unsupported provider runtime: {provider}")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Gemini provider requires the google-genai package. Install it with: pip install -U google-genai"
        ) from exc

    http_options = types.HttpOptions(timeout=timeout_ms)
    return ProviderRuntimeClient(
        provider=provider,
        client=genai.Client(api_key=api_key, http_options=http_options),
        types=types,
    )


def run_model_request(
    *,
    runtime: ProviderRuntimeClient,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    input_payload: Any,
    response_schema: dict[str, Any],
    schema_validator: RuntimeValidator,
    temperature: float,
    max_output_tokens: int,
    max_retries: int,
    retry_sleep_seconds: float,
    log_prefix: str | None = None,
    log_fn: RuntimeLogger | None = None,
) -> ModelRequestResult:
    prompt_hash = _sha256_text(system_prompt)
    input_hash = _hash_input_payload(input_payload)
    attempt_failures: list[dict[str, Any]] = []
    request_started_at = time.monotonic()

    if provider != runtime.provider:
        failure = _build_attempt_failure(
            attempt=1,
            status="bad_request",
            message=f"Provider mismatch: requested {provider}, runtime is {runtime.provider}.",
            raw_response_text=None,
            raw_response_present=False,
            json_parse_ok=False,
            json_repaired=False,
            schema_valid=False,
            error_type="ProviderMismatchError",
            latency_ms=0,
        )
        metadata = _build_result_metadata(
            provider=provider,
            model=model,
            prompt_hash=prompt_hash,
            input_hash=input_hash,
            attempt_count=1,
            raw_response_present=False,
            json_parse_ok=False,
            json_repaired=False,
            schema_valid=False,
            final_status="bad_request",
            latency_ms=0,
        )
        return ModelRequestResult(
            ok=False,
            payload=None,
            metadata=metadata,
            attempt_failures=[failure],
            failure=failure,
            raw_response_text=None,
        )

    for attempt in range(1, max_retries + 1):
        if log_fn is not None and log_prefix:
            log_fn(f"[gemini] {log_prefix} attempt={attempt}/{max_retries}")

        attempt_started_at = time.monotonic()
        try:
            response = runtime.client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=runtime.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
            (
                payload,
                raw_response_text,
                raw_response_present,
                json_parse_ok,
                json_repaired,
                schema_valid,
            ) = _extract_and_validate_response(response=response, schema_validator=schema_validator)
            metadata = _build_result_metadata(
                provider=provider,
                model=model,
                prompt_hash=prompt_hash,
                input_hash=input_hash,
                attempt_count=attempt,
                raw_response_present=raw_response_present,
                json_parse_ok=json_parse_ok,
                json_repaired=json_repaired,
                schema_valid=schema_valid,
                final_status="ok",
                latency_ms=int((time.monotonic() - request_started_at) * 1000),
            )
            return ModelRequestResult(
                ok=True,
                payload=payload,
                metadata=metadata,
                attempt_failures=attempt_failures,
                failure=None,
                raw_response_text=raw_response_text,
            )
        except KeyboardInterrupt as exc:
            failure = _build_attempt_failure(
                attempt=attempt,
                status="runtime_interrupted",
                message=_compact_text(str(exc)) or "Runtime interrupted.",
                raw_response_text=None,
                raw_response_present=False,
                json_parse_ok=False,
                json_repaired=False,
                schema_valid=False,
                error_type=type(exc).__name__,
                latency_ms=int((time.monotonic() - attempt_started_at) * 1000),
            )
        except _StructuredRuntimeError as exc:
            failure = _build_attempt_failure(
                attempt=attempt,
                status=exc.status,
                message=_compact_text(str(exc)),
                raw_response_text=exc.raw_response_text,
                raw_response_present=exc.raw_response_present,
                json_parse_ok=exc.json_parse_ok,
                json_repaired=exc.json_repaired,
                schema_valid=exc.schema_valid,
                error_type=exc.error_type,
                latency_ms=int((time.monotonic() - attempt_started_at) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            status = _classify_provider_exception(exc)
            failure = _build_attempt_failure(
                attempt=attempt,
                status=status,
                message=_compact_text(str(exc)) or status,
                raw_response_text=getattr(exc, "raw_payload_text", None),
                raw_response_present=bool(getattr(exc, "raw_payload_text", None)),
                json_parse_ok=False,
                json_repaired=False,
                schema_valid=False,
                error_type=type(exc).__name__,
                latency_ms=int((time.monotonic() - attempt_started_at) * 1000),
            )

        attempt_failures.append(failure)
        if log_fn is not None and log_prefix:
            log_fn(
                f"[gemini] {log_prefix} attempt={attempt}/{max_retries} failed={failure['error_type']}: {failure['message']}"
            )

        if not _should_retry(failure["failure_status"], attempt=attempt, max_retries=max_retries):
            metadata = _build_result_metadata(
                provider=provider,
                model=model,
                prompt_hash=prompt_hash,
                input_hash=input_hash,
                attempt_count=attempt,
                raw_response_present=failure["raw_response_present"],
                json_parse_ok=failure["json_parse_ok"],
                json_repaired=failure["json_repaired"],
                schema_valid=failure["schema_valid"],
                final_status=failure["failure_status"],
                latency_ms=int((time.monotonic() - request_started_at) * 1000),
            )
            return ModelRequestResult(
                ok=False,
                payload=None,
                metadata=metadata,
                attempt_failures=attempt_failures,
                failure=failure,
                raw_response_text=failure["raw_response_text"],
            )

        time.sleep(retry_sleep_seconds * attempt)

    last_failure = attempt_failures[-1]
    metadata = _build_result_metadata(
        provider=provider,
        model=model,
        prompt_hash=prompt_hash,
        input_hash=input_hash,
        attempt_count=max_retries,
        raw_response_present=last_failure["raw_response_present"],
        json_parse_ok=last_failure["json_parse_ok"],
        json_repaired=last_failure["json_repaired"],
        schema_valid=last_failure["schema_valid"],
        final_status=last_failure["failure_status"],
        latency_ms=int((time.monotonic() - request_started_at) * 1000),
    )
    return ModelRequestResult(
        ok=False,
        payload=None,
        metadata=metadata,
        attempt_failures=attempt_failures,
        failure=last_failure,
        raw_response_text=last_failure["raw_response_text"],
    )


def _extract_and_validate_response(
    *,
    response: Any,
    schema_validator: RuntimeValidator,
) -> tuple[Any, str | None, bool, bool, bool, bool]:
    parsed_payload = getattr(response, "parsed", None)
    if isinstance(parsed_payload, dict):
        raw_response_text = _serialize_response_payload(parsed_payload)
        raw_response_present = raw_response_text is not None
        payload = parsed_payload
        json_parse_ok = True
        json_repaired = False
    else:
        response_text = getattr(response, "text", None)
        if response_text:
            payload, json_repaired = _parse_json_response(response_text)
            raw_response_text = response_text
            raw_response_present = True
            json_parse_ok = True
        elif parsed_payload is not None:
            raw_response_text = _serialize_response_payload(parsed_payload)
            raise _StructuredRuntimeError(
                status="schema_invalid",
                message=f"Provider parsed payload into {type(parsed_payload).__name__}, expected a JSON object.",
                raw_response_text=raw_response_text,
                raw_response_present=raw_response_text is not None,
                json_parse_ok=False,
                json_repaired=False,
                schema_valid=False,
                error_type=type(parsed_payload).__name__,
            )
        else:
            raise _StructuredRuntimeError(
                status="empty_response",
                message="Provider returned an empty response.",
                raw_response_text=None,
                raw_response_present=False,
                json_parse_ok=False,
                json_repaired=False,
                schema_valid=False,
                error_type="EmptyResponseError",
            )

    try:
        validated_payload = schema_validator(payload)
    except Exception as exc:  # noqa: BLE001
        raise _StructuredRuntimeError(
            status="schema_invalid",
            message=f"Schema validation failed: {_compact_text(str(exc)) or type(exc).__name__}",
            raw_response_text=raw_response_text,
            raw_response_present=raw_response_present,
            json_parse_ok=json_parse_ok,
            json_repaired=json_repaired,
            schema_valid=False,
            error_type=type(exc).__name__,
        ) from exc

    return (
        validated_payload,
        raw_response_text,
        raw_response_present,
        json_parse_ok,
        json_repaired,
        True,
    )


def _parse_json_response(text: str) -> tuple[Any, bool]:
    raw = _normalize_json_text(text)
    try:
        return json.loads(raw), False
    except json.JSONDecodeError as exc:
        repaired = _repair_json_text(raw)
        if not repaired:
            raise _StructuredRuntimeError(
                status="malformed_json",
                message=f"Provider returned invalid JSON: {exc}",
                raw_response_text=raw,
                raw_response_present=True,
                json_parse_ok=False,
                json_repaired=False,
                schema_valid=False,
                error_type="JSONDecodeError",
            ) from exc
        try:
            return json.loads(repaired), True
        except json.JSONDecodeError as inner_exc:
            raise _StructuredRuntimeError(
                status="json_repair_failed",
                message=f"Provider returned invalid JSON after repair: {inner_exc}",
                raw_response_text=raw,
                raw_response_present=True,
                json_parse_ok=False,
                json_repaired=False,
                schema_valid=False,
                error_type="JSONDecodeError",
            ) from inner_exc


def _repair_json_text(text: str) -> str | None:
    candidate = text.strip()
    repaired = candidate
    if repaired.startswith("```"):
        repaired = repaired.strip("`").strip()
        if repaired.lower().startswith("json"):
            repaired = repaired[4:].strip()
    if repaired != candidate:
        candidate = repaired

    if candidate == text.strip():
        return None
    return candidate


def _classify_provider_exception(exc: Exception) -> str:
    message = str(exc).upper()
    status_code = getattr(exc, "status_code", None)
    if "RESOURCE_EXHAUSTED" in message or "QUOTA EXCEEDED" in message:
        return "quota_exhausted"
    if status_code == 429:
        return "rate_limited"
    if status_code == 503 or "UNAVAILABLE" in message or "HIGH DEMAND" in message:
        return "provider_overloaded"
    if status_code is not None and 400 <= status_code < 500:
        return "bad_request"
    return "transport_error"


def _should_retry(status: str, *, attempt: int, max_retries: int) -> bool:
    if attempt >= max_retries:
        return False
    return status in {
        "rate_limited",
        "provider_overloaded",
        "transport_error",
        "empty_response",
        "malformed_json",
        "json_repair_failed",
        "schema_invalid",
    }


def _build_attempt_failure(
    *,
    attempt: int,
    status: str,
    message: str,
    raw_response_text: str | None,
    raw_response_present: bool,
    json_parse_ok: bool,
    json_repaired: bool,
    schema_valid: bool,
    error_type: str,
    latency_ms: int,
) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "failure_status": status,
        "message": message,
        "error_type": error_type,
        "raw_response_text": raw_response_text,
        "raw_response_present": raw_response_present,
        "json_parse_ok": json_parse_ok,
        "json_repaired": json_repaired,
        "schema_valid": schema_valid,
        "latency_ms": latency_ms,
    }


def _build_result_metadata(
    *,
    provider: str,
    model: str,
    prompt_hash: str,
    input_hash: str,
    attempt_count: int,
    raw_response_present: bool,
    json_parse_ok: bool,
    json_repaired: bool,
    schema_valid: bool,
    final_status: str,
    latency_ms: int,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "prompt_hash": prompt_hash,
        "input_hash": input_hash,
        "attempt_count": attempt_count,
        "retry_count": max(0, attempt_count - 1),
        "raw_response_present": raw_response_present,
        "json_parse_ok": json_parse_ok,
        "json_repaired": json_repaired,
        "schema_valid": schema_valid,
        "final_status": final_status,
        "latency_ms": latency_ms,
    }


def _normalize_json_text(text: str) -> str:
    return str(text or "").strip().lstrip("\ufeff")


def _serialize_response_payload(payload: Any) -> str | None:
    if payload is None:
        return None
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except TypeError:
        text = _compact_text(payload)
        return text or None


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _hash_input_payload(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return _sha256_canonical_json(value)
    return _sha256_text(str(value or ""))


def _sha256_canonical_json(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
