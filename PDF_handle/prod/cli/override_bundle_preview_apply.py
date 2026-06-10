from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import ensure_dir, read_json, utc_timestamp, write_json
from PDF_handle.prod.core.site_data import build_site_data_paths
from PDF_handle.prod.core.site_roots import get_work_site_root
from PDF_handle.prod.schema.overrides import normalize_override_bundle, validate_override_bundle


SANDBOX_ROOT_MARKERS = ("\\sites\\work\\", "\\sandbox_sites\\", "/sites/work/", "/sandbox_sites/")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply a preview override bundle to a sandbox/work site root only, with "
            "backup and before/after artifact capture."
        )
    )
    parser.add_argument("--site-root", type=Path, default=None)
    parser.add_argument("--preview-bundle", type=Path, required=True)
    parser.add_argument(
        "--expected-live-sha256",
        default=None,
        help="Optional expected sha256 of the current live override file. Abort if it drifted.",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=PDF_HANDLE_ROOT / "runs" / "override_language_update",
    )
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if the preview bundle fails schema validation.")
    return parser


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def site_root_is_sandbox_like(site_root: Path) -> bool:
    normalized = str(site_root.resolve()).replace("/", "\\").lower()
    return any(marker.strip("\\").lower() in normalized for marker in SANDBOX_ROOT_MARKERS)


def bundle_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "override_count": len(bundle.get("overrides", [])),
        "field_count": sum(len((record.get("fields") or {}).keys()) for record in bundle.get("overrides", [])),
    }


def diff_summary(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_by_key = {
        (
            str(record.get("identity", {}).get("degree") or "").strip(),
            str(record.get("identity", {}).get("slug") or "").strip(),
            str(record.get("identity", {}).get("language") or "").strip(),
        ): record
        for record in before.get("overrides", [])
    }
    after_by_key = {
        (
            str(record.get("identity", {}).get("degree") or "").strip(),
            str(record.get("identity", {}).get("slug") or "").strip(),
            str(record.get("identity", {}).get("language") or "").strip(),
        ): record
        for record in after.get("overrides", [])
    }
    changed: list[dict[str, Any]] = []
    all_keys = sorted(set(before_by_key) | set(after_by_key))
    for key in all_keys:
        before_record = before_by_key.get(key)
        after_record = after_by_key.get(key)
        if before_record is None or after_record is None:
            changed.append(
                {
                    "identity": {"degree": key[0], "slug": key[1], "language": key[2] or None},
                    "change": "record_added_or_removed",
                }
            )
            continue
        before_fields = set((before_record.get("fields") or {}).keys())
        after_fields = set((after_record.get("fields") or {}).keys())
        removed_fields = sorted(before_fields - after_fields)
        added_fields = sorted(after_fields - before_fields)
        changed_fields = sorted(
            field for field in (before_fields & after_fields)
            if before_record["fields"].get(field) != after_record["fields"].get(field)
        )
        if removed_fields or added_fields or changed_fields:
            changed.append(
                {
                    "identity": {"degree": key[0], "slug": key[1], "language": key[2] or None},
                    "removed_fields": removed_fields,
                    "added_fields": added_fields,
                    "changed_fields": changed_fields,
                }
            )
    return {
        "changed_record_count": len(changed),
        "changed_records": changed,
    }


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "site_root", None) is None:
        args.site_root = get_work_site_root()
    site_root = args.site_root.resolve()
    if not site_root_is_sandbox_like(site_root):
        raise SystemExit("Preview override apply is sandbox/work only. Refusing to target a non-sandbox root.")

    site_paths = build_site_data_paths(site_root)
    live_overrides_path = site_paths["overrides"]
    report_dir = ensure_dir(
        args.report_dir.resolve()
        if args.report_dir
        else (args.report_root.resolve() / utc_timestamp().replace(":", "-"))
    )

    before_bytes = live_overrides_path.read_bytes() if live_overrides_path.exists() else b""
    before_sha = sha256_bytes(before_bytes)
    if args.expected_live_sha256 and before_sha != args.expected_live_sha256:
        raise SystemExit(
            f"Current live override bundle SHA drifted. expected={args.expected_live_sha256} current={before_sha}"
        )

    before_bundle = normalize_override_bundle(
        read_json(live_overrides_path) if live_overrides_path.exists() else {"overrides": []},
        site_root=site_root,
    )
    preview_bundle = normalize_override_bundle(read_json(args.preview_bundle.resolve()), site_root=site_root)
    preview_schema_report = validate_override_bundle(preview_bundle, site_root=site_root)
    if args.strict and not preview_schema_report["ok"]:
        raise SystemExit("Preview bundle failed schema validation.")

    write_json(report_dir / "content.overrides.before.json", before_bundle)
    write_json(report_dir / "content.overrides.preview.json", preview_bundle)

    write_json(live_overrides_path, preview_bundle)

    after_bundle = normalize_override_bundle(read_json(live_overrides_path), site_root=site_root)
    after_sha = sha256_file(live_overrides_path)
    apply_report = {
        "created_at": utc_timestamp(),
        "site_root": str(site_root),
        "live_overrides_path": str(live_overrides_path),
        "preview_bundle_path": str(args.preview_bundle.resolve()),
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "before": bundle_summary(before_bundle),
        "after": bundle_summary(after_bundle),
        "preview_schema_report": preview_schema_report,
        "diff_summary": diff_summary(before_bundle, after_bundle),
    }
    write_json(report_dir / "override_bundle_preview_apply_report.json", apply_report)
    print(json.dumps(apply_report["diff_summary"], ensure_ascii=False), flush=True)
    print(f"[done] preview override bundle applied to {live_overrides_path}", flush=True)


if __name__ == "__main__":
    main()
