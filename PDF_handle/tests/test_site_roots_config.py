"""Site-roots re-baseline contract (systemic plan WS3).

A clean checkout must not search for old-workspace paths (``0.3``,
``sites/live/v0.4-current``, ``published_sites``, ...). Site roots come from an
explicit ``--site-root`` or from ``sites/site_roots.json``; when neither
exists, the error must point at the committed template.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.core import site_roots

EXAMPLE_CONFIG = REPO_ROOT / "sites" / "site_roots.example.json"
RUNTIME_FIXTURE = REPO_ROOT / "data" / "fixtures" / "runtime_site_root"

LEGACY_ROOT_VALUES = {
    "0.3",
    "0.3-copy",
    "sandbox_sites",
    "published_sites",
    "sites/live/v0.4-current",
    "sites/work/v0.4",
}


class TestNoBakedInSiteRoots(unittest.TestCase):
    def test_defaults_are_empty(self) -> None:
        self.assertEqual(
            site_roots.DEFAULT_SITE_ROOTS_CONFIG,
            {},
            "A clean checkout must not carry baked-in site roots",
        )

    def test_unconfigured_lookup_points_at_the_template(self) -> None:
        missing_config = Path(tempfile.gettempdir()) / "no_such_site_roots.json"
        with mock.patch.object(site_roots, "SITE_ROOTS_CONFIG_PATH", missing_config):
            with self.assertRaises(FileNotFoundError) as ctx:
                site_roots.get_work_site_root()
        self.assertIn("site_roots.example.json", str(ctx.exception))

    def test_configured_root_resolves_through_the_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "site_roots.json"
            config_path.write_text(
                json.dumps({"work_site_root": str(RUNTIME_FIXTURE)}),
                encoding="utf-8",
            )
            with mock.patch.object(site_roots, "SITE_ROOTS_CONFIG_PATH", config_path):
                resolved = site_roots.get_work_site_root()
        self.assertEqual(resolved, RUNTIME_FIXTURE.resolve())


class TestExampleConfigTemplate(unittest.TestCase):
    def test_example_parses_with_expected_keys(self) -> None:
        payload = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
        for key in ("live_site_root", "work_site_root", "published_sites_root"):
            self.assertIn(key, payload)

    def test_example_names_no_old_workspace_paths(self) -> None:
        payload = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
        legacy = set(payload.values()) & LEGACY_ROOT_VALUES
        self.assertEqual(legacy, set(), f"example config still names legacy roots: {legacy}")

    def test_js_lane_carries_no_legacy_defaults(self) -> None:
        js_text = (REPO_ROOT / "PDF_handle" / "TOOLS" / "lib" / "site_roots.js").read_text(
            encoding="utf-8"
        )
        for marker in ("v0.4-current", "0.3-copy"):
            self.assertNotIn(marker, js_text, f"site_roots.js still defaults to {marker}")


if __name__ == "__main__":
    unittest.main()
