from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from PDF_handle.prod.providers.result import (
    ProviderError,
    ProviderResult,
    classify_error_kind,
    timed,
)


class MalformedProviderPayloadError(ProviderError):
    error_kind = "malformed_payload"


def get_gemini_client(api_key: str | None) -> tuple[Any, Any]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Gemini provider requires the google-genai package. Install it with: pip install -U google-genai"
        ) from exc

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client()
    return client, types


def generate_content_rest(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    api_key: str | None,
    thinking_budget: int | None = None,
    response_mime_type: str | None = None,
    response_schema: Any | None = None,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError(
            "Gemini REST fallback requires an API key in the configured env var."
        )

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(model, safe='')}:generateContent?key={urllib.parse.quote(api_key, safe='')}"
    )
    generation_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    if thinking_budget is not None:
        generation_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type
    if response_schema is not None:
        generation_config["responseSchema"] = response_schema

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": generation_config,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini REST fallback HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini REST fallback network error: {exc}") from exc

    candidates = response_payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini REST fallback returned no candidates: {response_payload}")

    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    response_text = "\n".join(
        str(part.get("text") or "").strip()
        for part in parts
        if str(part.get("text") or "").strip()
    ).strip()
    if not response_text:
        raise RuntimeError(f"Gemini REST fallback returned empty text: {response_payload}")

    usage_metadata = response_payload.get("usageMetadata")
    if usage_metadata is not None:
        usage_metadata = json.dumps(usage_metadata, ensure_ascii=False)

    return {
        "response_text": response_text,
        "parsed": None,
        "usage_metadata": usage_metadata,
        "transport": "rest-fallback",
    }


def generate_content(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    api_key: str | None,
    thinking_budget: int | None = None,
    response_mime_type: str | None = None,
    response_schema: Any | None = None,
) -> dict[str, Any]:
    try:
        client, types = get_gemini_client(api_key)
    except RuntimeError as exc:
        if "google-genai package" not in str(exc):
            raise
        return generate_content_rest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            api_key=api_key,
            thinking_budget=thinking_budget,
            response_mime_type=response_mime_type,
            response_schema=response_schema,
        )

    config_kwargs: dict[str, Any] = {
        "system_instruction": system_prompt,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if thinking_budget is not None and hasattr(types, "ThinkingConfig"):
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
    if response_mime_type:
        config_kwargs["response_mime_type"] = response_mime_type
    if response_schema is not None:
        config_kwargs["response_schema"] = response_schema

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    response_text = getattr(response, "text", None)
    if isinstance(response_text, str):
        response_text = response_text.strip() or None
    parsed_payload = getattr(response, "parsed", None)
    if response_text is None and parsed_payload is None:
        raise RuntimeError("Gemini returned an empty response.")

    usage_metadata = getattr(response, "usage_metadata", None)
    if usage_metadata is not None:
        usage_metadata = str(usage_metadata)

    return {
        "response_text": response_text,
        "parsed": parsed_payload,
        "usage_metadata": usage_metadata,
        "transport": "google-genai",
    }


def run_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    api_key: str | None,
    thinking_budget: int | None = None,
) -> ProviderResult:
    """Text-mode call returning the uniform, non-throwing ProviderResult."""
    with timed() as timer:
        try:
            raw = generate_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                api_key=api_key,
                thinking_budget=thinking_budget,
            )
            text = str(raw.get("response_text") or "").strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response.")
        except Exception as exc:
            timer.__exit__(None, None, None)
            return ProviderResult(
                provider="gemini",
                model=model,
                duration_seconds=timer.elapsed,
                error_kind=classify_error_kind(exc),
                error_message=str(exc),
                exception=exc,
            )
    return ProviderResult(
        provider="gemini",
        model=model,
        transport=raw.get("transport"),
        text=text,
        usage_metadata=raw.get("usage_metadata"),
        duration_seconds=timer.elapsed,
    )


def generate_text_content(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    api_key: str | None,
    thinking_budget: int | None = None,
) -> dict[str, Any]:
    result = run_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        api_key=api_key,
        thinking_budget=thinking_budget,
    ).raise_for_error()
    return {
        "response_text": result.text,
        "usage_metadata": result.usage_metadata,
        "transport": result.transport,
        "model": result.model,
        "duration_seconds": result.duration_seconds,
    }


def extract_json_payload(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise MalformedProviderPayloadError(f"Gemini returned invalid JSON: {exc}") from exc
        try:
            payload = json.loads(raw[start : end + 1])
        except json.JSONDecodeError as inner_exc:
            raise MalformedProviderPayloadError(f"Gemini returned invalid JSON: {inner_exc}") from inner_exc
    if not isinstance(payload, dict):
        raise MalformedProviderPayloadError(
            f"Gemini response parsed into {type(payload).__name__}, expected a JSON object."
        )
    return payload


def run_json(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    api_key: str | None,
    thinking_budget: int | None = None,
    response_mime_type: str | None = None,
    response_schema: Any | None = None,
) -> ProviderResult:
    """JSON-mode call returning the uniform, non-throwing ProviderResult."""
    with timed() as timer:
        try:
            raw = generate_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                api_key=api_key,
                thinking_budget=thinking_budget,
                response_mime_type=response_mime_type,
                response_schema=response_schema,
            )
            parsed_payload = raw.get("parsed")
            if isinstance(parsed_payload, dict):
                payload = parsed_payload
            else:
                response_text = raw.get("response_text")
                if not response_text:
                    raise MalformedProviderPayloadError("Gemini returned an empty JSON response.")
                payload = extract_json_payload(response_text)
        except Exception as exc:
            timer.__exit__(None, None, None)
            return ProviderResult(
                provider="gemini",
                model=model,
                duration_seconds=timer.elapsed,
                error_kind=classify_error_kind(exc),
                error_message=str(exc),
                exception=exc,
            )
    return ProviderResult(
        provider="gemini",
        model=model,
        transport=raw.get("transport"),
        text=raw.get("response_text"),
        payload=payload,
        usage_metadata=raw.get("usage_metadata"),
        duration_seconds=timer.elapsed,
    )


def generate_json_content(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    api_key: str | None,
    thinking_budget: int | None = None,
    response_mime_type: str | None = None,
    response_schema: Any | None = None,
) -> dict[str, Any]:
    result = run_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        api_key=api_key,
        thinking_budget=thinking_budget,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    ).raise_for_error()
    return {
        "payload": result.payload,
        "usage_metadata": result.usage_metadata,
        "transport": result.transport,
        "model": result.model,
        "duration_seconds": result.duration_seconds,
    }
