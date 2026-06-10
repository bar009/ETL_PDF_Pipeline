"""Offline ETL smoke over the committed fixtures — no PDFs, no providers, no network.

The smallest useful proof that the staging→apply→runtime path is alive:

1. copy the runtime fixture site root into a temp directory
2. confirm it satisfies the site-root contract
3. normalize + validate the degree data (pre-state)
4. apply the staged fixture patch (the real merge layer, not a mock)
5. re-apply the same patch and require an identical result (idempotency)
6. validate the merged result and require the provenance marker
7. write the merged file back through the atomic writer and re-check the root

Exit code 0 means the minimal ETL path works on a clean checkout.
Run it from anywhere:

    python PDF_handle/prod/cli/smoke_fixture.py
    python PDF_handle/prod/cli/smoke_fixture.py --report PDF_handle/runs/smoke_fixture/report.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import read_json, utc_timestamp, write_json
from PDF_handle.prod.core.site_roots import _looks_like_site_root
from PDF_handle.prod.schema.data import (
    custom_validate_degree_data,
    normalize_degree_data,
    serialize_degree_data,
)
from PDF_handle.prod.schema.patches import apply_degree_patches

RUNTIME_FIXTURE = REPO_ROOT / "data" / "fixtures" / "runtime_site_root"
STAGING_FIXTURE = REPO_ROOT / "data" / "fixtures" / "staging_minimal"


def run_smoke() -> dict[str, Any]:
    report: dict[str, Any] = {
        "tool": "smoke_fixture",
        "started_at": utc_timestamp(),
        "steps": [],
        "errors": [],
    }

    def step(name: str, ok: bool, detail: str = "") -> bool:
        report["steps"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            report["errors"].append(f"{name}: {detail}")
        return ok

    with tempfile.TemporaryDirectory(prefix="smoke_fixture_") as tmp:
        site_root = Path(tmp) / "site_root"
        shutil.copytree(RUNTIME_FIXTURE, site_root)

        if not step(
            "site_root_contract",
            _looks_like_site_root(site_root),
            f"{site_root} must contain data/content.schema.json",
        ):
            return _finish(report)

        raw = read_json(site_root / "data" / "level1.json")
        degree_data = normalize_degree_data(raw, "level1")
        pre = custom_validate_degree_data(degree_data)
        if not step("pre_state_valid", pre["ok"], "; ".join(pre["errors"])):
            return _finish(report)

        patch_payload = read_json(STAGING_FIXTURE / "level1.patch.json")
        operations = patch_payload.get("operations", [])
        if not step("staged_operations_present", bool(operations), "staging fixture has no operations"):
            return _finish(report)

        merged = apply_degree_patches(degree_data, operations)
        first_pass = json.dumps(serialize_degree_data(merged), ensure_ascii=False, sort_keys=True)

        merged_again = apply_degree_patches(merged, operations)
        second_pass = json.dumps(serialize_degree_data(merged_again), ensure_ascii=False, sort_keys=True)
        step("apply_is_idempotent", first_pass == second_pass, "re-applying the same patch changed the result")

        target_slug = operations[0]["slug"]
        marker_id = operations[0]["marker_id"]
        target = merged_again["entryBySlug"].get(target_slug, {})
        step(
            "provenance_marker_present",
            marker_id in target.get("full_summary", ""),
            f"marker {marker_id} missing from {target_slug}.full_summary",
        )

        post = custom_validate_degree_data(merged_again)
        step("merged_state_valid", post["ok"], "; ".join(post["errors"]))

        write_json(site_root / "data" / "level1.json", serialize_degree_data(merged_again))
        reread = read_json(site_root / "data" / "level1.json")
        step(
            "runtime_write_roundtrip",
            custom_validate_degree_data(normalize_degree_data(reread, "level1"))["ok"]
            and _looks_like_site_root(site_root),
            "merged runtime file failed validation after atomic write",
        )

    return _finish(report)


def _finish(report: dict[str, Any]) -> dict[str, Any]:
    report["finished_at"] = utc_timestamp()
    report["ok"] = not report["errors"]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline ETL smoke over the committed fixtures (no PDFs, no providers)."
    )
    parser.add_argument(
        "--report", type=Path, default=None,
        help="Optional path for the JSON report (directories created as needed).",
    )
    args = parser.parse_args()

    report = run_smoke()

    if args.report is not None:
        write_json(args.report, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
