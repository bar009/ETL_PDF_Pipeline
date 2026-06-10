"""The uniform provider result contract (WS7). No network, no SDK required."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.providers import gemini
from PDF_handle.prod.providers.gemini import MalformedProviderPayloadError
from PDF_handle.prod.providers.result import (
    ERROR_KINDS,
    ProviderError,
    classify_error_kind,
)

CALL_KWARGS = dict(
    system_prompt="s",
    user_prompt="u",
    model="gemini-test",
    temperature=0.1,
    max_output_tokens=64,
    api_key="not-a-real-key",
)


class TestErrorClassification(unittest.TestCase):
    def test_explicit_kind_wins(self) -> None:
        self.assertEqual(
            classify_error_kind(MalformedProviderPayloadError("bad")), "malformed_payload"
        )

    def test_message_heuristics(self) -> None:
        cases = {
            "Gemini provider requires the google-genai package.": "dependency",
            "Gemini REST fallback requires an API key in the configured env var.": "auth",
            "Gemini REST fallback HTTP 429: quota exceeded": "rate_limit",
            "Gemini REST fallback network error: timed out": "transport",
            "Gemini returned an empty response.": "empty_response",
            "something entirely different": "unknown",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(classify_error_kind(RuntimeError(message)), expected)

    def test_all_kinds_are_declared(self) -> None:
        self.assertIn("unknown", ERROR_KINDS)
        self.assertEqual(len(ERROR_KINDS), len(set(ERROR_KINDS)))


class TestRunText(unittest.TestCase):
    def test_success_shape(self) -> None:
        fake = {
            "response_text": "  answer  ",
            "parsed": None,
            "usage_metadata": "tokens=42",
            "transport": "google-genai",
        }
        with mock.patch.object(gemini, "generate_content", return_value=fake):
            result = gemini.run_text(**CALL_KWARGS)
        self.assertTrue(result.ok)
        self.assertEqual(result.text, "answer")
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.model, "gemini-test")
        self.assertEqual(result.transport, "google-genai")
        self.assertEqual(result.usage_metadata, "tokens=42")
        self.assertGreaterEqual(result.duration_seconds, 0.0)
        self.assertIsNone(result.error_kind)
        self.assertNotIn("exception", result.to_dict())

    def test_failure_is_structured_not_thrown(self) -> None:
        boom = RuntimeError("Gemini REST fallback HTTP 429: quota exceeded")
        with mock.patch.object(gemini, "generate_content", side_effect=boom):
            result = gemini.run_text(**CALL_KWARGS)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_kind, "rate_limit")
        self.assertIs(result.exception, boom)

    def test_raise_for_error_reraises_the_original_exception(self) -> None:
        boom = MalformedProviderPayloadError("Gemini returned invalid JSON: x")
        with mock.patch.object(gemini, "generate_content", side_effect=boom):
            result = gemini.run_text(**CALL_KWARGS)
        with self.assertRaises(MalformedProviderPayloadError):
            result.raise_for_error()

    def test_empty_response_is_classified(self) -> None:
        fake = {"response_text": "  ", "parsed": None, "usage_metadata": None, "transport": "x"}
        with mock.patch.object(gemini, "generate_content", return_value=fake):
            result = gemini.run_text(**CALL_KWARGS)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_kind, "empty_response")


class TestRunJson(unittest.TestCase):
    def test_parsed_payload_wins(self) -> None:
        fake = {"response_text": None, "parsed": {"a": 1}, "usage_metadata": None, "transport": "x"}
        with mock.patch.object(gemini, "generate_content", return_value=fake):
            result = gemini.run_json(**CALL_KWARGS)
        self.assertTrue(result.ok)
        self.assertEqual(result.payload, {"a": 1})

    def test_text_payload_is_extracted(self) -> None:
        fake = {
            "response_text": '```json\n{"b": 2}\n```',
            "parsed": None,
            "usage_metadata": None,
            "transport": "x",
        }
        with mock.patch.object(gemini, "generate_content", return_value=fake):
            result = gemini.run_json(**CALL_KWARGS)
        self.assertTrue(result.ok)
        self.assertEqual(result.payload, {"b": 2})

    def test_malformed_payload_is_classified(self) -> None:
        fake = {"response_text": "not json at all", "parsed": None, "usage_metadata": None, "transport": "x"}
        with mock.patch.object(gemini, "generate_content", return_value=fake):
            result = gemini.run_json(**CALL_KWARGS)
        self.assertFalse(result.ok)
        self.assertEqual(result.error_kind, "malformed_payload")


class TestLegacyDelegates(unittest.TestCase):
    def test_generate_text_content_keeps_legacy_keys(self) -> None:
        fake = {"response_text": "t", "parsed": None, "usage_metadata": "u", "transport": "x"}
        with mock.patch.object(gemini, "generate_content", return_value=fake):
            payload = gemini.generate_text_content(**CALL_KWARGS)
        for key in ("response_text", "usage_metadata", "transport"):
            self.assertIn(key, payload)
        self.assertEqual(payload["response_text"], "t")

    def test_generate_json_content_raises_the_original_type(self) -> None:
        fake = {"response_text": "not json", "parsed": None, "usage_metadata": None, "transport": "x"}
        with mock.patch.object(gemini, "generate_content", return_value=fake):
            with self.assertRaises(MalformedProviderPayloadError):
                gemini.generate_json_content(**CALL_KWARGS)

    def test_provider_error_hierarchy_is_stable(self) -> None:
        # stage.py matches on MalformedProviderPayloadError and RuntimeError.
        self.assertTrue(issubclass(MalformedProviderPayloadError, ProviderError))
        self.assertTrue(issubclass(ProviderError, RuntimeError))


if __name__ == "__main__":
    unittest.main()
