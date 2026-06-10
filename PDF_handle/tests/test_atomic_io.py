from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "PDF_handle")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PDF_handle.prod.core.io import read_json, read_text, write_json, write_json_group, write_text


class WriteJsonAtomicTest(unittest.TestCase):
    def test_round_trip_with_unicode(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.json"
            payload = {"hebrew": "אהבה", "english": "love", "list": [1, 2, 3]}
            write_json(p, payload)
            self.assertEqual(read_json(p), payload)

    def test_leaves_no_tmp_file_on_success(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "out.json"
            write_json(target, {"x": 1})
            leftover = list(Path(td).glob("*.tmp"))
            self.assertEqual(leftover, [])

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.json"
            write_json(p, {"v": 1})
            write_json(p, {"v": 2})
            self.assertEqual(read_json(p), {"v": 2})

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a" / "b" / "c.json"
            write_json(p, {"ok": True})
            self.assertTrue(p.exists())


class WriteJsonGroupTest(unittest.TestCase):
    def test_commits_all_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            a, b, c = base / "a.json", base / "sub" / "b.json", base / "c.json"
            write_json_group([(a, {"n": 1}), (b, {"n": 2}), (c, {"n": 3})])
            self.assertEqual(read_json(a), {"n": 1})
            self.assertEqual(read_json(b), {"n": 2})
            self.assertEqual(read_json(c), {"n": 3})

    def test_leaves_no_tmp_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            write_json_group([(base / "a.json", {"x": 1}), (base / "b.json", {"x": 2})])
            self.assertEqual(list(base.glob("*.tmp")), [])

    def test_serialization_failure_touches_no_target(self):
        # A non-serializable payload in the batch must abort before any target is
        # written, leaving previously-existing targets untouched and no tmp residue.
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            good = base / "good.json"
            write_json(good, {"original": True})
            bad_payload = {"obj": object()}  # not JSON-serializable
            with self.assertRaises(TypeError):
                write_json_group([(good, {"original": False}), (base / "bad.json", bad_payload)])
            self.assertEqual(read_json(good), {"original": True})
            self.assertFalse((base / "bad.json").exists())
            self.assertEqual(list(base.glob("*.tmp")), [])


class WriteTextAtomicTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.txt"
            write_text(p, "hello\nworld\n")
            self.assertEqual(read_text(p), "hello\nworld\n")

    def test_round_trip_utf8_bom_tolerated_on_read(self):
        # write_text emits UTF-8 without BOM; read_text accepts utf-8-sig so a BOM-bearing
        # source file is still readable. Verify the BOM round-trip behavior used by
        # downstream merges.
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "withbom.txt"
            p.write_bytes("﻿title\n".encode("utf-8"))
            self.assertEqual(read_text(p), "title\n")


if __name__ == "__main__":
    unittest.main()
