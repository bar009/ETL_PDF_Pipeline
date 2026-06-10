from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF_HANDLE_ROOT = REPO_ROOT / "PDF_handle"
for candidate in (REPO_ROOT, PDF_HANDLE_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from PDF_handle.prod.core.io import utc_timestamp
from PDF_handle.prod.exploration import (
    build_clusters,
    create_run_dir,
    normalize_external_reviews,
    reconcile_clusters,
    require_step5_artifacts,
    write_exploration_reports,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build typed exploration graph clusters from Step 5 staged artifacts, "
            "optionally ingest external semantic review JSON, and produce reconciliation "
            "reports under PDF_handle/runs/ without mutating live site data."
        )
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=PDF_HANDLE_ROOT / "staged_injection",
        help="Step 5 staged artifact directory.",
    )
    parser.add_argument(
        "--external-review-json",
        type=Path,
        default=None,
        help="Optional external semantic review JSON (vendor-neutral normalized input).",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=None,
        help="Optional custom root for exploration run artifacts (defaults to PDF_handle/runs/exploration_review).",
    )
    parser.add_argument("--max-cluster-nodes", type=int, default=25)
    parser.add_argument("--max-cluster-edges", type=int, default=60)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    staging_dir = args.staging_dir.resolve()
    require_step5_artifacts(staging_dir)
    clusters = build_clusters(
        staging_dir,
        max_nodes=args.max_cluster_nodes,
        max_edges=args.max_cluster_edges,
    )

    external_reviews = []
    if args.external_review_json is not None:
        external_reviews = normalize_external_reviews(args.external_review_json.resolve())

    reconciliation_report = reconcile_clusters(clusters, external_reviews)
    run_dir = create_run_dir(args.run_root)
    run_manifest = {
        "created_at": utc_timestamp(),
        "tool": "prod.cli.exploration_review",
        "staging_dir": str(staging_dir),
        "external_review_json": str(args.external_review_json.resolve()) if args.external_review_json else None,
        "cluster_count": len(clusters),
        "external_review_count": len(external_reviews),
        "mutates_live_data": False,
        "intended_integration_point": "after_step5_before_step6_optional",
    }
    outputs = write_exploration_reports(
        run_dir=run_dir,
        run_manifest=run_manifest,
        clusters=clusters,
        external_reviews=external_reviews,
        reconciliation_report=reconciliation_report,
    )
    print(f"[done] exploration review artifacts written to {run_dir}", flush=True)
    print(f"[summary] clusters={len(clusters)} external_reviews={len(external_reviews)}", flush=True)
    print(f"[report] reconciliation={outputs['reconciliation_report']}", flush=True)


if __name__ == "__main__":
    main()
