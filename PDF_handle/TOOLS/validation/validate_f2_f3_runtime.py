from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

TOOLS_DIR = Path(__file__).resolve().parents[1]
PDF_HANDLE_ROOT = TOOLS_DIR.parent
CODE_ROOT = PDF_HANDLE_ROOT.parent
if str(PDF_HANDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(PDF_HANDLE_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from pipeline_utils import utc_timestamp
from workspace_paths import get_work_site_root

import content_routing_review as f3
import provider_runtime as runtime
import semantic_system_purity_review as f2


REQUIRED_ROW_PROVENANCE_KEYS = (
    "provider",
    "model",
    "prompt_hash",
    "input_hash",
    "attempt_count",
    "retry_count",
    "raw_response_present",
    "json_parse_ok",
    "json_repaired",
    "schema_valid",
    "final_provider_status",
    "processed_at",
)


@dataclass
class ValidationResult:
    name: str
    target: str
    passed: bool
    details: str


class ValidationFailure(RuntimeError):
    pass


class FakeProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeGenerateContentConfig:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeResponse:
    def __init__(self, *, text: str | None = None, parsed: Any = None) -> None:
        self.text = text
        self.parsed = parsed


class FakeModels:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def generate_content(self, **_: Any) -> Any:
        if not self._responses:
            raise RuntimeError("No fake responses remaining.")
        self.calls += 1
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_dir(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        raise ValidationFailure(f"{message}: expected={expected!r} got={actual!r}")


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run_cli(command: list[str], *, expect_returncode: int | None = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    if expect_returncode is not None and completed.returncode != expect_returncode:
        raise ValidationFailure(
            f"Command returned {completed.returncode}, expected {expect_returncode}.\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )
    return completed


def run_validation_step(
    results: list[ValidationResult],
    *,
    name: str,
    target: str,
    step: Callable[[], str],
) -> str | None:
    try:
        details = step()
    except Exception as exc:  # noqa: BLE001
        results.append(
            ValidationResult(
                name=name,
                target=target,
                passed=False,
                details=str(exc),
            )
        )
        return None
    results.append(
        ValidationResult(
            name=name,
            target=target,
            passed=True,
            details=details,
        )
    )
    return details


@contextmanager
def patched_attr(obj: Any, attr_name: str, value: Any):
    original = getattr(obj, attr_name)
    setattr(obj, attr_name, value)
    try:
        yield
    finally:
        setattr(obj, attr_name, original)


def make_runtime_metadata(
    *,
    final_status: str,
    input_hash: str,
    prompt_hash: str = "p" * 64,
    attempt_count: int = 1,
    retry_count: int | None = None,
    raw_response_present: bool = True,
    json_parse_ok: bool = True,
    json_repaired: bool = False,
    schema_valid: bool = True,
    latency_ms: int = 11,
) -> dict[str, Any]:
    return {
        "provider": "gemini",
        "model": "fake-gemini",
        "prompt_hash": prompt_hash,
        "input_hash": input_hash,
        "attempt_count": attempt_count,
        "retry_count": retry_count if retry_count is not None else max(0, attempt_count - 1),
        "raw_response_present": raw_response_present,
        "json_parse_ok": json_parse_ok,
        "json_repaired": json_repaired,
        "schema_valid": schema_valid,
        "final_status": final_status,
        "latency_ms": latency_ms,
    }


def make_failure(
    *,
    status: str,
    attempt: int,
    message: str | None = None,
    raw_response_text: str | None = None,
    raw_response_present: bool = True,
    json_parse_ok: bool = False,
    json_repaired: bool = False,
    schema_valid: bool = False,
    error_type: str = "SyntheticError",
    latency_ms: int = 7,
) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "failure_status": status,
        "message": message or status,
        "error_type": error_type,
        "raw_response_text": raw_response_text,
        "raw_response_present": raw_response_present,
        "json_parse_ok": json_parse_ok,
        "json_repaired": json_repaired,
        "schema_valid": schema_valid,
        "latency_ms": latency_ms,
    }


def build_runtime_result(
    *,
    ok: bool,
    input_hash: str,
    payload: Any = None,
    final_status: str,
    attempt_failures: list[dict[str, Any]] | None = None,
    failure: dict[str, Any] | None = None,
    json_repaired: bool = False,
    json_parse_ok: bool = True,
    schema_valid: bool = True,
    attempt_count: int = 1,
) -> runtime.ModelRequestResult:
    metadata = make_runtime_metadata(
        final_status=final_status,
        input_hash=input_hash,
        attempt_count=attempt_count,
        json_repaired=json_repaired,
        json_parse_ok=json_parse_ok,
        schema_valid=schema_valid,
        raw_response_present=bool(payload is not None or failure),
    )
    return runtime.ModelRequestResult(
        ok=ok,
        payload=payload,
        metadata=metadata,
        attempt_failures=attempt_failures or [],
        failure=failure,
        raw_response_text=(failure or {}).get("raw_response_text"),
    )


def flatten_f2_rows(entry_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for entry in entry_rows for row in entry.get("paragraph_reviews", []) if isinstance(row, dict)]


def flatten_f3_rows(entry_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for entry in entry_rows for row in entry.get("routing_reviews", []) if isinstance(row, dict)]


def assert_required_row_provenance(row: dict[str, Any], *, target: str) -> None:
    for key in REQUIRED_ROW_PROVENANCE_KEYS:
        assert_true(key in row, f"{target} row is missing provenance key: {key}")


def verify_f2_summary(summary: dict[str, Any], entry_rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    rows = flatten_f2_rows(entry_rows)
    completed = sum(1 for row in rows if row.get("unit_processing_status") == "completed")
    skipped = sum(1 for row in rows if row.get("unit_processing_status") == "skipped")
    failed = sum(1 for row in rows if row.get("unit_processing_status") == "failed")
    pending = summary.get("total_units", 0) - completed - skipped - failed
    assert_equal(summary.get("completed_units"), completed, "F2 completed_units mismatch")
    assert_equal(summary.get("skipped_units"), skipped, "F2 skipped_units mismatch")
    assert_equal(summary.get("failed_units"), failed, "F2 failed_units mismatch")
    assert_equal(summary.get("pending_units"), pending, "F2 pending_units mismatch")
    assert_equal(
        summary.get("repair_applied_count"),
        sum(1 for row in rows if row.get("json_repaired")),
        "F2 repair_applied_count mismatch",
    )
    failure_counts: dict[str, int] = {}
    for row in failures:
        status = row.get("failure_status")
        if status:
            failure_counts[status] = failure_counts.get(status, 0) + 1
    assert_equal(summary.get("malformed_json_count"), failure_counts.get("malformed_json", 0), "F2 malformed count mismatch")
    assert_equal(
        summary.get("json_repair_failed_count"),
        failure_counts.get("json_repair_failed", 0),
        "F2 json_repair_failed count mismatch",
    )
    assert_equal(summary.get("schema_invalid_count"), failure_counts.get("schema_invalid", 0), "F2 schema_invalid count mismatch")
    assert_equal(summary.get("rate_limit_count"), failure_counts.get("rate_limited", 0), "F2 rate_limited count mismatch")
    assert_equal(
        summary.get("provider_overloaded_count"),
        failure_counts.get("provider_overloaded", 0),
        "F2 provider_overloaded count mismatch",
    )
    assert_true(summary.get("run_manifest_path"), "F2 summary is missing run_manifest_path")
    assert_equal(summary.get("summary_schema_version"), f2.SUMMARY_SCHEMA_VERSION, "F2 summary schema version mismatch")
    assert_equal(summary.get("row_schema_version"), f2.ROW_SCHEMA_VERSION, "F2 row schema version mismatch")
    if rows:
        assert_required_row_provenance(rows[0], target="F2")


def verify_f3_summary(summary: dict[str, Any], entry_rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    rows = flatten_f3_rows(entry_rows)
    completed = sum(1 for row in rows if row.get("unit_processing_status") == "completed")
    skipped = sum(1 for row in rows if row.get("unit_processing_status") == "skipped")
    failed = sum(1 for row in rows if row.get("unit_processing_status") == "failed")
    pending = summary.get("total_units", 0) - completed - skipped - failed
    assert_equal(summary.get("completed_units"), completed, "F3 completed_units mismatch")
    assert_equal(summary.get("skipped_units"), skipped, "F3 skipped_units mismatch")
    assert_equal(summary.get("failed_units"), failed, "F3 failed_units mismatch")
    assert_equal(summary.get("pending_units"), pending, "F3 pending_units mismatch")
    assert_equal(
        summary.get("repair_applied_count"),
        sum(1 for row in rows if row.get("json_repaired")),
        "F3 repair_applied_count mismatch",
    )
    failure_counts: dict[str, int] = {}
    for row in failures:
        status = row.get("failure_status")
        if status:
            failure_counts[status] = failure_counts.get(status, 0) + 1
    assert_equal(summary.get("malformed_json_count"), failure_counts.get("malformed_json", 0), "F3 malformed count mismatch")
    assert_equal(
        summary.get("json_repair_failed_count"),
        failure_counts.get("json_repair_failed", 0),
        "F3 json_repair_failed count mismatch",
    )
    assert_equal(summary.get("schema_invalid_count"), failure_counts.get("schema_invalid", 0), "F3 schema_invalid count mismatch")
    assert_equal(summary.get("rate_limit_count"), failure_counts.get("rate_limited", 0), "F3 rate_limited count mismatch")
    assert_equal(
        summary.get("provider_overloaded_count"),
        failure_counts.get("provider_overloaded", 0),
        "F3 provider_overloaded count mismatch",
    )
    assert_true(summary.get("run_manifest_path"), "F3 summary is missing run_manifest_path")
    assert_equal(summary.get("summary_schema_version"), f3.SUMMARY_SCHEMA_VERSION, "F3 summary schema version mismatch")
    assert_equal(summary.get("row_schema_version"), f3.ROW_SCHEMA_VERSION, "F3 row schema version mismatch")
    if rows:
        assert_required_row_provenance(rows[0], target="F3")


def fake_runtime_client(*responses: Any) -> runtime.ProviderRuntimeClient:
    models = FakeModels(list(responses))
    client = SimpleNamespace(models=models)
    types = SimpleNamespace(GenerateContentConfig=FakeGenerateContentConfig)
    return runtime.ProviderRuntimeClient(provider="gemini", client=client, types=types)


def validator_with_answer(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or "answer" not in payload:
        raise ValueError("Missing answer key.")
    return payload


def base_f2_entry() -> dict[str, Any]:
    return {
        "slug": "synthetic-cable-tow",
        "title": "Synthetic Cable Tow",
        "type": "symbolism",
        "category": "synthetic",
        "parent_topic": None,
        "related_topics": {},
        "symbolic_meaning": "A plain symbolic paragraph with no external-system framing.",
    }


def base_f3_source_entry() -> dict[str, Any]:
    return {
        "slug": "synthetic-cable-tow",
        "title": "Synthetic Cable Tow",
        "type": "symbolism",
        "category": "synthetic",
        "parent_topic": None,
        "related_topics": {},
    }


def base_f3_row() -> dict[str, Any]:
    return {
        "review_unit_id": "synthetic-cable-tow::symbolic_meaning::p1",
        "field_name": "symbolic_meaning",
        "paragraph_index": 1,
        "text_excerpt": "A synthetic paragraph for routing validation.",
        "paragraph_char_count": 80,
        "oversized_paragraph": False,
        "detected_system_family": "ambiguous",
        "semantic_verdict": "uncertain",
        "detection_confidence": "low",
        "is_comparative": False,
        "is_framed": False,
        "final_verdict": "manual_review",
        "recommended_preservation_action": "move_to_library_or_research",
        "recommended_destination": "library/research",
        "manual_review_reason": "model_retry_exhausted",
        "decision_source": "gemini",
        "provider_status": "validation_failed",
        "lexical_overlay": {
            "matched": False,
            "matched_families": [],
            "matched_labels": [],
            "f1_rule_hints": [],
            "agreement_with_semantic": "none",
        },
        "explanation": "Synthetic routing row.",
    }


def test_provider_runtime_repair_success() -> str:
    runtime_client = fake_runtime_client(FakeResponse(text="```json\n{\"answer\": \"ok\"}\n```"))
    result = runtime.run_model_request(
        runtime=runtime_client,
        provider="gemini",
        model="fake-gemini",
        system_prompt="Return JSON.",
        user_prompt="Answer.",
        input_payload={"prompt": "answer"},
        response_schema={},
        schema_validator=validator_with_answer,
        temperature=0.1,
        max_output_tokens=256,
        max_retries=2,
        retry_sleep_seconds=0.0,
    )
    assert_true(result.ok, "Repair-success runtime test did not succeed.")
    assert_true(result.metadata["json_repaired"], "Repair-success runtime test did not mark json_repaired.")
    return "repair success path produced json_repaired=true"


def test_provider_runtime_repair_failure() -> str:
    runtime_client = fake_runtime_client(FakeResponse(text="prefix {\"answer\": \"ok\",} suffix"))
    result = runtime.run_model_request(
        runtime=runtime_client,
        provider="gemini",
        model="fake-gemini",
        system_prompt="Return JSON.",
        user_prompt="Answer.",
        input_payload={"prompt": "answer"},
        response_schema={},
        schema_validator=validator_with_answer,
        temperature=0.1,
        max_output_tokens=256,
        max_retries=1,
        retry_sleep_seconds=0.0,
    )
    assert_true(not result.ok, "Repair-failure runtime test unexpectedly succeeded.")
    assert_equal(result.failure["failure_status"], "json_repair_failed", "Repair-failure status mismatch")
    return "repair failure path produced json_repair_failed"


def test_f2_runtime_integration() -> str:
    entry = base_f2_entry()
    review_context = f2.prepare_review_context(
        entry=entry,
        field_name="symbolic_meaning",
        paragraph_index=1,
        paragraph=entry["symbolic_meaning"],
        previous_paragraph=None,
        whitelist=[],
    )
    success_payload = {
        "detected_system_family": "blue_lodge_symbolic",
        "detection_confidence": "high",
        "semantic_verdict": "fits_expected_family",
        "is_comparative": False,
        "is_framed": False,
        "framing_source": "none",
        "recommended_preservation_action": "keep_here_framed",
        "recommended_destination": None,
        "explanation": "Synthetic validated payload.",
    }
    success_result = build_runtime_result(
        ok=True,
        input_hash=review_context["review_input_hash"],
        payload=success_payload,
        final_status="ok",
        json_repaired=True,
    )
    failure = make_failure(status="json_repair_failed", attempt=3)
    failure_result = build_runtime_result(
        ok=False,
        input_hash=review_context["review_input_hash"],
        final_status="json_repair_failed",
        attempt_failures=[failure],
        failure=failure,
        json_parse_ok=False,
        schema_valid=False,
        attempt_count=3,
    )
    rate_limited_failure = make_failure(status="rate_limited", attempt=3)
    rate_limited_result = build_runtime_result(
        ok=False,
        input_hash=review_context["review_input_hash"],
        final_status="rate_limited",
        attempt_failures=[rate_limited_failure],
        failure=rate_limited_failure,
        json_parse_ok=False,
        schema_valid=False,
        attempt_count=3,
    )
    overloaded_failure = make_failure(status="provider_overloaded", attempt=3)
    overloaded_result = build_runtime_result(
        ok=False,
        input_hash=review_context["review_input_hash"],
        final_status="provider_overloaded",
        attempt_failures=[overloaded_failure],
        failure=overloaded_failure,
        json_parse_ok=False,
        schema_valid=False,
        attempt_count=3,
    )

    failed_attempts: list[dict[str, Any]] = []
    with patched_attr(f2, "run_model_request", lambda **_: success_result):
        row = f2.review_paragraph(
            entry=entry,
            review_context=review_context,
            provider="gemini",
            model="fake-gemini",
            system_prompt="synthetic prompt",
            slug_map={entry["slug"]: entry},
            provider_runtime=object(),
            gemini_failed_attempts=failed_attempts,
            quiet=True,
        )
    assert_true(row["json_repaired"], "F2 success row did not preserve json_repaired provenance.")
    assert_equal(row["final_provider_status"], "ok", "F2 success final_provider_status mismatch")
    assert_required_row_provenance(row, target="F2 synthetic success")

    failed_attempts = []
    with patched_attr(f2, "run_model_request", lambda **_: failure_result):
        failure_row = f2.review_paragraph(
            entry=entry,
            review_context=review_context,
            provider="gemini",
            model="fake-gemini",
            system_prompt="synthetic prompt",
            slug_map={entry["slug"]: entry},
            provider_runtime=object(),
            gemini_failed_attempts=failed_attempts,
            quiet=True,
        )
    assert_equal(failure_row["unit_processing_status"], "failed", "F2 failed row did not mark unit_processing_status=failed")
    assert_equal(failure_row["final_provider_status"], "json_repair_failed", "F2 failed row final_provider_status mismatch")
    assert_equal(failed_attempts[0]["failure_status"], "json_repair_failed", "F2 failure log mismatch")

    with patched_attr(f2, "run_model_request", lambda **_: rate_limited_result):
        try:
            f2.review_paragraph(
                entry=entry,
                review_context=review_context,
                provider="gemini",
                model="fake-gemini",
                system_prompt="synthetic prompt",
                slug_map={entry["slug"]: entry},
                provider_runtime=object(),
                gemini_failed_attempts=[],
                quiet=True,
            )
        except f2.SemanticReviewInterrupted as exc:
            assert_equal(exc.reason, "rate_limited", "F2 rate-limited interrupt reason mismatch")
        else:
            raise ValidationFailure("F2 rate-limited test did not interrupt.")

    with patched_attr(f2, "run_model_request", lambda **_: overloaded_result):
        try:
            f2.review_paragraph(
                entry=entry,
                review_context=review_context,
                provider="gemini",
                model="fake-gemini",
                system_prompt="synthetic prompt",
                slug_map={entry["slug"]: entry},
                provider_runtime=object(),
                gemini_failed_attempts=[],
                quiet=True,
            )
        except f2.SemanticReviewInterrupted as exc:
            assert_equal(exc.reason, "provider_overloaded", "F2 overloaded interrupt reason mismatch")
        else:
            raise ValidationFailure("F2 provider-overloaded test did not interrupt.")

    return "repair success/failure and 429/503 interruption paths validated through review_paragraph"


def test_f3_runtime_integration() -> str:
    taxonomy = f3.load_taxonomy(f3.DEFAULT_TAXONOMY_FILE)
    source_entry = base_f3_source_entry()
    row = base_f3_row()
    routing_context = f3.prepare_routing_context(
        row=row,
        source_entry=source_entry,
        existing_shortlist=[],
        slug_map={},
        taxonomy=taxonomy,
    )
    success_route = {
        "preservation_value": "medium",
        "routing_decision": "move_to_library",
        "routing_confidence": "medium",
        "target_kind": "library_research",
        "target_slug": None,
        "future_entry_label": None,
        "library_bucket": f3.DEFAULT_LIBRARY_BUCKET,
        "taxonomy_match_reason": "no_safe_existing_slug",
        "rewrite_needed": False,
        "cleanup_priority": "medium",
        "explanation": "Synthetic validated route.",
    }
    success_result = build_runtime_result(
        ok=True,
        input_hash=routing_context["routing_input_hash"],
        payload=success_route,
        final_status="ok",
        json_repaired=True,
    )
    failure = make_failure(status="json_repair_failed", attempt=3)
    failure_result = build_runtime_result(
        ok=False,
        input_hash=routing_context["routing_input_hash"],
        final_status="json_repair_failed",
        attempt_failures=[failure],
        failure=failure,
        json_parse_ok=False,
        schema_valid=False,
        attempt_count=3,
    )
    rate_limited_failure = make_failure(status="rate_limited", attempt=3)
    rate_limited_result = build_runtime_result(
        ok=False,
        input_hash=routing_context["routing_input_hash"],
        final_status="rate_limited",
        attempt_failures=[rate_limited_failure],
        failure=rate_limited_failure,
        json_parse_ok=False,
        schema_valid=False,
        attempt_count=3,
    )
    overloaded_failure = make_failure(status="provider_overloaded", attempt=3)
    overloaded_result = build_runtime_result(
        ok=False,
        input_hash=routing_context["routing_input_hash"],
        final_status="provider_overloaded",
        attempt_failures=[overloaded_failure],
        failure=overloaded_failure,
        json_parse_ok=False,
        schema_valid=False,
        attempt_count=3,
    )

    failed_attempts: list[dict[str, Any]] = []
    with patched_attr(f3, "run_model_request", lambda **_: success_result):
        routing_row = f3.review_routing_unit(
            row=row,
            source_entry=source_entry,
            existing_shortlist=[],
            slug_map={},
            taxonomy=taxonomy,
            routing_context=routing_context,
            provider="gemini",
            model="fake-gemini",
            system_prompt="synthetic prompt",
            provider_runtime=object(),
            gemini_failed_attempts=failed_attempts,
            quiet=True,
        )
    assert_true(routing_row["json_repaired"], "F3 success row did not preserve json_repaired provenance.")
    assert_equal(routing_row["final_provider_status"], "ok", "F3 success final_provider_status mismatch")
    assert_required_row_provenance(routing_row, target="F3 synthetic success")

    failed_attempts = []
    with patched_attr(f3, "run_model_request", lambda **_: failure_result):
        failure_row = f3.review_routing_unit(
            row=row,
            source_entry=source_entry,
            existing_shortlist=[],
            slug_map={},
            taxonomy=taxonomy,
            routing_context=routing_context,
            provider="gemini",
            model="fake-gemini",
            system_prompt="synthetic prompt",
            provider_runtime=object(),
            gemini_failed_attempts=failed_attempts,
            quiet=True,
        )
    assert_equal(failure_row["unit_processing_status"], "failed", "F3 failed row did not mark unit_processing_status=failed")
    assert_equal(failure_row["final_provider_status"], "json_repair_failed", "F3 failed row final_provider_status mismatch")
    assert_equal(failed_attempts[0]["failure_status"], "json_repair_failed", "F3 failure log mismatch")

    with patched_attr(f3, "run_model_request", lambda **_: rate_limited_result):
        try:
            f3.review_routing_unit(
                row=row,
                source_entry=source_entry,
                existing_shortlist=[],
                slug_map={},
                taxonomy=taxonomy,
                routing_context=routing_context,
                provider="gemini",
                model="fake-gemini",
                system_prompt="synthetic prompt",
                provider_runtime=object(),
                gemini_failed_attempts=[],
                quiet=True,
            )
        except f3.ContentRoutingInterrupted as exc:
            assert_equal(exc.reason, "rate_limited", "F3 rate-limited interrupt reason mismatch")
        else:
            raise ValidationFailure("F3 rate-limited test did not interrupt.")

    with patched_attr(f3, "run_model_request", lambda **_: overloaded_result):
        try:
            f3.review_routing_unit(
                row=row,
                source_entry=source_entry,
                existing_shortlist=[],
                slug_map={},
                taxonomy=taxonomy,
                routing_context=routing_context,
                provider="gemini",
                model="fake-gemini",
                system_prompt="synthetic prompt",
                provider_runtime=object(),
                gemini_failed_attempts=[],
                quiet=True,
            )
        except f3.ContentRoutingInterrupted as exc:
            assert_equal(exc.reason, "provider_overloaded", "F3 overloaded interrupt reason mismatch")
        else:
            raise ValidationFailure("F3 provider-overloaded test did not interrupt.")

    return "repair success/failure and 429/503 interruption paths validated through review_routing_unit"


def test_f2_cli_suite(base_dir: Path, *, site_root: Path, slug: str) -> dict[str, Any]:
    script = TOOLS_DIR / "semantic_system_purity_review.py"
    fresh_dir = base_dir / "f2_fresh"
    interrupted_dir = base_dir / "f2_interrupted"
    old_dir = base_dir / "f2_legacy_dir"
    reset_dir(fresh_dir)
    reset_dir(interrupted_dir)
    reset_dir(old_dir)
    write_text(old_dir / "legacy.txt", "legacy report dir without manifest")

    base_command = [
        sys.executable,
        str(script),
        "--site-root",
        str(site_root),
        "--slug",
        slug,
        "--provider",
        "heuristic",
        "--strict",
    ]

    run_cli(base_command + ["--report-dir", str(fresh_dir)])
    summary = read_json(fresh_dir / "semantic_purity_summary.json")
    entries = read_json(fresh_dir / "semantic_purity_entries.json")
    failures = read_json(fresh_dir / f2.GEMINI_FAILURE_ARTIFACT)
    verify_f2_summary(summary, entries, failures)
    assert_true((fresh_dir / f2.RUN_MANIFEST_ARTIFACT).exists(), "F2 fresh run did not create run_manifest.json")
    assert_true((fresh_dir / f2.RESUME_STATE_ARTIFACT).exists(), "F2 fresh run did not create resume state")
    summary_snapshot = (fresh_dir / "semantic_purity_summary.json").read_text(encoding="utf-8")

    rerun = subprocess.run(
        base_command + ["--report-dir", str(fresh_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(rerun.returncode != 0, "F2 same-dir rerun without --resume did not fail fast.")
    assert_true("Use --resume" in (rerun.stdout + rerun.stderr), "F2 rerun failure message was not clear.")
    assert_equal(
        (fresh_dir / "semantic_purity_summary.json").read_text(encoding="utf-8"),
        summary_snapshot,
        "F2 same-dir rerun mutated existing artifacts",
    )

    incompatible = subprocess.run(
        [
            sys.executable,
            str(script),
            "--site-root",
            str(site_root),
            "--provider",
            "heuristic",
            "--strict",
            "--report-dir",
            str(fresh_dir),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(incompatible.returncode != 0, "F2 incompatible rerun did not fail fast.")
    assert_true("Run manifest mismatch" in (incompatible.stdout + incompatible.stderr), "F2 incompatible rerun was not classified clearly.")
    assert_equal(
        (fresh_dir / "semantic_purity_summary.json").read_text(encoding="utf-8"),
        summary_snapshot,
        "F2 incompatible rerun mutated existing artifacts",
    )

    old_run = subprocess.run(
        base_command + ["--report-dir", str(old_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(old_run.returncode != 0, "F2 legacy report_dir test did not fail fast.")
    assert_true(
        not (old_dir / "semantic_purity_summary.json").exists(),
        "F2 legacy report_dir test polluted the old directory with new artifacts.",
    )

    interrupted = subprocess.run(
        base_command
        + [
            "--report-dir",
            str(interrupted_dir),
            "--max-runtime-seconds",
            "0.001",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(interrupted.returncode != 0, "F2 max-runtime test did not interrupt under --strict.")
    interrupted_summary = read_json(interrupted_dir / "semantic_purity_summary.json")
    assert_equal(interrupted_summary["run_status"], "interrupted", "F2 interrupted run_status mismatch")

    run_cli(base_command + ["--report-dir", str(interrupted_dir), "--resume"])
    resumed_summary = read_json(interrupted_dir / "semantic_purity_summary.json")
    resumed_entries = read_json(interrupted_dir / "semantic_purity_entries.json")
    resumed_failures = read_json(interrupted_dir / f2.GEMINI_FAILURE_ARTIFACT)
    verify_f2_summary(resumed_summary, resumed_entries, resumed_failures)
    assert_equal(resumed_summary["pending_units"], 0, "F2 resumed run still has pending units")

    run_cli(base_command + ["--report-dir", str(fresh_dir), "--resume"])
    resumed_completed_summary = read_json(fresh_dir / "semantic_purity_summary.json")
    verify_f2_summary(resumed_completed_summary, read_json(fresh_dir / "semantic_purity_entries.json"), failures)

    return {
        "fresh_dir": str(fresh_dir),
        "resumed_dir": str(interrupted_dir),
    }


def test_f3_cli_suite(base_dir: Path, *, site_root: Path, f2_report_dir: Path, slug: str) -> dict[str, Any]:
    script = TOOLS_DIR / "content_routing_review.py"
    fresh_dir = base_dir / "f3_fresh"
    interrupted_dir = base_dir / "f3_interrupted"
    old_dir = base_dir / "f3_legacy_dir"
    reset_dir(fresh_dir)
    reset_dir(interrupted_dir)
    reset_dir(old_dir)
    write_text(old_dir / "legacy.txt", "legacy report dir without manifest")

    base_command = [
        sys.executable,
        str(script),
        "--f2-report-dir",
        str(f2_report_dir),
        "--site-root",
        str(site_root),
        "--slug",
        slug,
        "--provider",
        "heuristic",
        "--strict",
    ]

    run_cli(base_command + ["--report-dir", str(fresh_dir)])
    summary = read_json(fresh_dir / "content_routing_summary.json")
    entries = read_json(fresh_dir / "content_routing_entries.json")
    failures = read_json(fresh_dir / f3.GEMINI_FAILURE_ARTIFACT)
    verify_f3_summary(summary, entries, failures)
    assert_true((fresh_dir / f3.RUN_MANIFEST_ARTIFACT).exists(), "F3 fresh run did not create run_manifest.json")
    assert_true((fresh_dir / f3.RESUME_STATE_ARTIFACT).exists(), "F3 fresh run did not create resume state")
    summary_snapshot = (fresh_dir / "content_routing_summary.json").read_text(encoding="utf-8")

    rerun = subprocess.run(
        base_command + ["--report-dir", str(fresh_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(rerun.returncode != 0, "F3 same-dir rerun without --resume did not fail fast.")
    assert_true("Use --resume" in (rerun.stdout + rerun.stderr), "F3 rerun failure message was not clear.")
    assert_equal(
        (fresh_dir / "content_routing_summary.json").read_text(encoding="utf-8"),
        summary_snapshot,
        "F3 same-dir rerun mutated existing artifacts",
    )

    taxonomy_variant = base_dir / "taxonomy_variant.json"
    taxonomy_payload = read_json(f3.DEFAULT_TAXONOMY_FILE)
    taxonomy_payload["library_buckets"][0]["description"] = "validation-matrix-variant"
    write_json(taxonomy_variant, taxonomy_payload)
    incompatible = subprocess.run(
        base_command + ["--report-dir", str(fresh_dir), "--taxonomy-file", str(taxonomy_variant), "--resume"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(incompatible.returncode != 0, "F3 incompatible rerun did not fail fast.")
    assert_true("Run manifest mismatch" in (incompatible.stdout + incompatible.stderr), "F3 incompatible rerun was not classified clearly.")
    assert_equal(
        (fresh_dir / "content_routing_summary.json").read_text(encoding="utf-8"),
        summary_snapshot,
        "F3 incompatible rerun mutated existing artifacts",
    )

    old_run = subprocess.run(
        base_command + ["--report-dir", str(old_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(old_run.returncode != 0, "F3 legacy report_dir test did not fail fast.")
    assert_true(
        not (old_dir / "content_routing_summary.json").exists(),
        "F3 legacy report_dir test polluted the old directory with new artifacts.",
    )

    interrupted = subprocess.run(
        base_command
        + [
            "--report-dir",
            str(interrupted_dir),
            "--max-runtime-seconds",
            "0.001",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        cwd=str(CODE_ROOT),
    )
    assert_true(interrupted.returncode != 0, "F3 max-runtime test did not interrupt under --strict.")
    interrupted_summary = read_json(interrupted_dir / "content_routing_summary.json")
    assert_equal(interrupted_summary["run_status"], "interrupted", "F3 interrupted run_status mismatch")

    run_cli(base_command + ["--report-dir", str(interrupted_dir), "--resume"])
    resumed_summary = read_json(interrupted_dir / "content_routing_summary.json")
    resumed_entries = read_json(interrupted_dir / "content_routing_entries.json")
    resumed_failures = read_json(interrupted_dir / f3.GEMINI_FAILURE_ARTIFACT)
    verify_f3_summary(resumed_summary, resumed_entries, resumed_failures)
    assert_equal(resumed_summary["pending_units"], 0, "F3 resumed run still has pending units")

    run_cli(base_command + ["--report-dir", str(fresh_dir), "--resume"])
    resumed_completed_summary = read_json(fresh_dir / "content_routing_summary.json")
    verify_f3_summary(resumed_completed_summary, read_json(fresh_dir / "content_routing_entries.json"), failures)

    return {
        "fresh_dir": str(fresh_dir),
        "resumed_dir": str(interrupted_dir),
    }


def render_results_markdown(results: list[ValidationResult], *, report_dir: Path) -> str:
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    lines = [
        "# F2/F3 Runtime Validation",
        "",
        f"- Generated at: `{utc_timestamp()}`",
        f"- Report dir: `{report_dir}`",
        f"- Passed: `{passed}`",
        f"- Failed: `{failed}`",
        "",
        "## Results",
        "",
    ]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"- [{status}] `{result.target}` `{result.name}`")
        lines.append(f"  {result.details}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase E validation matrix for F2/F3 runtime reliability.")
    parser.add_argument("--site-root", type=Path, default=get_work_site_root())
    parser.add_argument("--slug", default="cable-tow")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=TOOLS_DIR / "reports" / "runtime_validation" / "phase_e",
    )
    args = parser.parse_args()

    timestamp_slug = utc_timestamp().replace(":", "-").replace("+00:00", "Z")
    run_dir = ensure_dir(args.report_dir.resolve()) / timestamp_slug
    ensure_dir(run_dir)

    results: list[ValidationResult] = []
    base_dir = run_dir / "artifacts"
    ensure_dir(base_dir)

    run_validation_step(
        results,
        name="provider-runtime repair success",
        target="provider_runtime",
        step=test_provider_runtime_repair_success,
    )
    run_validation_step(
        results,
        name="provider-runtime repair failure",
        target="provider_runtime",
        step=test_provider_runtime_repair_failure,
    )
    run_validation_step(
        results,
        name="F2 direct runtime integration",
        target="F2",
        step=test_f2_runtime_integration,
    )
    run_validation_step(
        results,
        name="F3 direct runtime integration",
        target="F3",
        step=test_f3_runtime_integration,
    )

    f2_result = run_validation_step(
        results,
        name="F2 CLI contract matrix",
        target="F2",
        step=lambda: json.dumps(
            test_f2_cli_suite(base_dir, site_root=args.site_root.resolve(), slug=args.slug),
            ensure_ascii=False,
        ),
    )

    f2_fresh_dir = None
    if f2_result is not None:
        f2_payload = json.loads(f2_result)
        f2_fresh_dir = Path(f2_payload["fresh_dir"])

    if f2_fresh_dir is not None:
        run_validation_step(
            results,
            name="F3 CLI contract matrix",
            target="F3",
            step=lambda: json.dumps(
                test_f3_cli_suite(
                    base_dir,
                    site_root=args.site_root.resolve(),
                    f2_report_dir=f2_fresh_dir,
                    slug=args.slug,
                ),
                ensure_ascii=False,
            ),
        )

    write_json(run_dir / "validation_results.json", [asdict(result) for result in results])
    write_text(run_dir / "F2_F3_RUNTIME_VALIDATION.md", render_results_markdown(results, report_dir=run_dir))

    if any(not result.passed for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
