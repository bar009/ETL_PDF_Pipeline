"""The canonical run-manifest shape (WS8).

The builder, the committed schema, and the first adopter (the fixture smoke)
must all agree. The structural check reads the required-key lists straight
from ``data/schemas/run_manifest.schema.json`` so the schema file is the
single source of truth even without the jsonschema package installed.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.smoke_fixture import run_smoke
from PDF_handle.prod.core.run_manifest import MANIFEST_FILENAME, RunManifest

SCHEMA_PATH = REPO_ROOT / "data" / "schemas" / "run_manifest.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_matches_schema(case: unittest.TestCase, manifest: dict) -> None:
    schema = _schema()
    for key in schema["required"]:
        case.assertIn(key, manifest, f"manifest missing required key {key}")
    for key in schema["properties"]["counts"]["required"]:
        case.assertIn(key, manifest["counts"], f"counts missing required key {key}")
    for step in manifest["steps"]:
        case.assertIn("name", step)
        case.assertIn("ok", step)


class TestRunManifestBuilder(unittest.TestCase):
    def test_builder_produces_the_committed_shape(self) -> None:
        manifest = RunManifest(tool="unit-test", inputs={"a": 1}, config={"b": 2})
        manifest.add_step("first", ok=True, counts={"items": 3})
        manifest.add_step("second", ok=False, detail="boom")
        manifest.add_warning("careful")
        manifest.add_output("out/report.json")
        manifest.add_provider_usage(
            {
                "provider": "gemini",
                "model": "gemini-test",
                "transport": "google-genai",
                "usage_metadata": "tokens=1",
                "duration_seconds": 0.5,
                "error_kind": None,
            }
        )
        payload = manifest.to_dict()

        _assert_matches_schema(self, payload)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"], ["second: boom"])
        self.assertEqual(payload["counts"]["steps"], 2)
        self.assertEqual(payload["counts"]["steps_failed"], 1)
        self.assertEqual(payload["counts"]["provider_calls"], 1)
        self.assertTrue(payload["run_id"].startswith("unit-test-"))
        self.assertGreaterEqual(payload["duration_seconds"], 0.0)

    def test_write_emits_run_manifest_json(self) -> None:
        manifest = RunManifest(tool="unit-test")
        manifest.add_step("only", ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = manifest.write(Path(tmp))
            self.assertEqual(path.name, MANIFEST_FILENAME)
            _assert_matches_schema(self, json.loads(path.read_text(encoding="utf-8")))


class TestSmokeEmitsTheManifestShape(unittest.TestCase):
    def test_smoke_report_is_a_valid_manifest(self) -> None:
        report = run_smoke()
        _assert_matches_schema(self, report)
        self.assertTrue(report["ok"])
        self.assertEqual(report["tool"], "smoke_fixture")
        self.assertEqual(report["config"], {"offline": True, "providers": "none"})


if __name__ == "__main__":
    unittest.main()
