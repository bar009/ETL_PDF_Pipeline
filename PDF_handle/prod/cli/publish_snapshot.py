"""Publish a frozen site snapshot after the strict runtime gate passes.

This CLI is local/offline by design. It copies an already-built site root into a
published snapshots directory, then writes the release gate report and
``run_manifest.json`` inside the snapshot.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.cli.validate_runtime import validate_runtime_site_root
from PDF_handle.prod.core.io import ensure_dir, write_json
from PDF_handle.prod.core.run_manifest import RunManifest
from PDF_handle.prod.core.site_roots import get_published_sites_root

GATE_REPORT_FILENAME = "release_gate_report.json"


def sanitize_name_segment(value: str) -> str:
    slug = re.sub(r"[^a-z0-9.-]+", "-", str(value or "").strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def infer_release_id(source_site_root: Path) -> str:
    match = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", source_site_root.name, re.IGNORECASE)
    return match.group(1) if match else "site"


def build_snapshot_name(
    *,
    source_site_root: Path,
    release_id: str | None = None,
    label: str = "live",
    qualifier: str = "",
    date: str | None = None,
) -> str:
    resolved_release_id = sanitize_name_segment(release_id or infer_release_id(source_site_root))
    resolved_label = sanitize_name_segment(label) or "live"
    resolved_qualifier = sanitize_name_segment(qualifier)
    resolved_date = date or datetime.now().astimezone().strftime("%Y-%m-%d")
    suffix = f"-{resolved_qualifier}" if resolved_qualifier else ""
    return f"{resolved_release_id}-{resolved_label}-{resolved_date}{suffix}"


def publish_snapshot(
    *,
    source_site_root: Path,
    published_root: Path,
    release_id: str | None = None,
    label: str = "live",
    qualifier: str = "",
    date: str | None = None,
) -> dict[str, Any]:
    source_site_root = Path(source_site_root).resolve()
    published_root = Path(published_root).resolve()
    snapshot_name = build_snapshot_name(
        source_site_root=source_site_root,
        release_id=release_id,
        label=label,
        qualifier=qualifier,
        date=date,
    )
    snapshot_root = published_root / snapshot_name

    manifest = RunManifest(
        tool="publish_snapshot",
        inputs={
            "source_site_root": str(source_site_root),
            "published_root": str(published_root),
        },
        config={
            "release_id": release_id,
            "label": label,
            "qualifier": qualifier,
            "date": date,
            "snapshot_name": snapshot_name,
        },
    )

    source_gate = validate_runtime_site_root(
        source_site_root,
        require_complete=True,
        strict=True,
    )
    if not manifest.add_step(
        "source_gate",
        ok=bool(source_gate["ok"]),
        detail="; ".join(source_gate["errors"] + source_gate["warnings"]),
    ):
        report = manifest.to_dict()
        report["source_gate_report"] = source_gate
        return report

    if snapshot_root.exists():
        manifest.add_step(
            "snapshot_target_available",
            ok=False,
            detail=f"snapshot already exists: {snapshot_root}",
        )
        return manifest.to_dict()
    manifest.add_step("snapshot_target_available", ok=True)

    ensure_dir(published_root)
    shutil.copytree(source_site_root, snapshot_root)
    manifest.add_step("copy_snapshot", ok=True)
    manifest.add_output(snapshot_root)

    snapshot_gate = validate_runtime_site_root(
        snapshot_root,
        require_complete=True,
        strict=True,
    )
    write_json(snapshot_root / GATE_REPORT_FILENAME, snapshot_gate)
    manifest.add_output(snapshot_root / GATE_REPORT_FILENAME)
    if not manifest.add_step(
        "snapshot_gate",
        ok=bool(snapshot_gate["ok"]),
        detail="; ".join(snapshot_gate["errors"] + snapshot_gate["warnings"]),
    ):
        manifest_path = snapshot_root / "run_manifest.json"
        manifest.add_output(manifest_path)
        report = manifest.to_dict()
        report["snapshot_root"] = str(snapshot_root)
        report["snapshot_gate_report"] = snapshot_gate
        write_json(manifest_path, report)
        return report

    manifest_path = snapshot_root / "run_manifest.json"
    manifest.add_output(manifest_path)
    report = manifest.to_dict()
    report["snapshot_root"] = str(snapshot_root)
    report["release_gate_report"] = str(snapshot_root / GATE_REPORT_FILENAME)
    report["run_manifest"] = str(manifest_path)
    write_json(manifest_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish a frozen site snapshot after the strict runtime gate passes."
    )
    parser.add_argument("--source-site-root", type=Path, required=True)
    parser.add_argument(
        "--published-root",
        type=Path,
        default=None,
        help="Published snapshots directory. Defaults to sites/site_roots.json published_sites_root.",
    )
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--label", default="live")
    parser.add_argument("--qualifier", default="")
    parser.add_argument(
        "--date",
        default=None,
        help="Override YYYY-MM-DD date segment; mainly for deterministic tests.",
    )
    args = parser.parse_args()

    published_root = args.published_root or get_published_sites_root()
    report = publish_snapshot(
        source_site_root=args.source_site_root,
        published_root=published_root,
        release_id=args.release_id,
        label=args.label,
        qualifier=args.qualifier,
        date=args.date,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
