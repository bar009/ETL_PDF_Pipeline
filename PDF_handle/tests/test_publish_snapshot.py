"""Release snapshot publishing must be gated, frozen, and self-describing."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.cli.publish_snapshot import (
    GATE_REPORT_FILENAME,
    build_snapshot_name,
    publish_snapshot,
)

RUNTIME_FIXTURE = REPO_ROOT / "data" / "fixtures" / "runtime_site_root"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PublishSnapshotCase(unittest.TestCase):
    def _complete_site_root(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="publish_snapshot_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        site_root = tmp / "source_site"
        shutil.copytree(RUNTIME_FIXTURE, site_root)

        level1 = _read_json(site_root / "data" / "level1.json")
        for entry in level1["entries"]:
            if entry.get("status") == "published" and not entry.get("source_notes"):
                entry["source_notes"] = ["Committed publish fixture source"]
        _write_json(site_root / "data" / "level1.json", level1)

        for degree_id in ("library", "level2", "level3"):
            payload = json.loads(json.dumps(level1))
            payload["meta"]["degree"] = degree_id
            payload["meta"]["title"] = f"{degree_id} publish fixture"
            for entry in payload["entries"]:
                entry["degree"] = degree_id
                entry["applies_to_degrees"] = [degree_id]
            _write_json(site_root / "data" / f"{degree_id}.json", payload)

        return site_root


class TestSnapshotNaming(unittest.TestCase):
    def test_snapshot_name_matches_release_model(self) -> None:
        name = build_snapshot_name(
            source_site_root=Path("sites/live/v2.0-current"),
            label="Live Site",
            qualifier="RC 1",
            date="2026-06-11",
        )
        self.assertEqual(name, "2.0-live-site-2026-06-11-rc-1")


class TestPublishSnapshot(PublishSnapshotCase):
    def test_publish_writes_gate_report_and_manifest_inside_snapshot(self) -> None:
        source = self._complete_site_root()
        with tempfile.TemporaryDirectory(prefix="published_root_") as tmp:
            report = publish_snapshot(
                source_site_root=source,
                published_root=Path(tmp),
                release_id="2.0",
                label="live",
                qualifier="test",
                date="2026-06-11",
            )

            snapshot = Path(report["snapshot_root"])
            self.assertTrue(report["ok"], report)
            self.assertEqual(snapshot.name, "2.0-live-2026-06-11-test")
            self.assertTrue((snapshot / "data" / "content.schema.json").exists())

            gate_report = _read_json(snapshot / GATE_REPORT_FILENAME)
            self.assertTrue(gate_report["ok"], gate_report)
            self.assertTrue(gate_report["strict"])

            manifest = _read_json(snapshot / "run_manifest.json")
            self.assertEqual(manifest["tool"], "publish_snapshot")
            self.assertTrue(manifest["ok"], manifest)
            self.assertIn(str(snapshot), manifest["outputs"])
            self.assertIn(str(snapshot / GATE_REPORT_FILENAME), manifest["outputs"])

    def test_publish_refuses_to_create_snapshot_when_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="published_root_") as tmp:
            report = publish_snapshot(
                source_site_root=RUNTIME_FIXTURE,
                published_root=Path(tmp),
                release_id="2.0",
                label="live",
                date="2026-06-11",
            )

            self.assertFalse(report["ok"], report)
            self.assertTrue(any(step["name"] == "source_gate" for step in report["steps"]))
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_publish_refuses_to_overwrite_existing_snapshot(self) -> None:
        source = self._complete_site_root()
        with tempfile.TemporaryDirectory(prefix="published_root_") as tmp:
            first = publish_snapshot(
                source_site_root=source,
                published_root=Path(tmp),
                release_id="2.0",
                label="live",
                date="2026-06-11",
            )
            second = publish_snapshot(
                source_site_root=source,
                published_root=Path(tmp),
                release_id="2.0",
                label="live",
                date="2026-06-11",
            )

            self.assertTrue(first["ok"], first)
            self.assertFalse(second["ok"], second)
            self.assertTrue(any("already exists" in error for error in second["errors"]))


if __name__ == "__main__":
    unittest.main()
