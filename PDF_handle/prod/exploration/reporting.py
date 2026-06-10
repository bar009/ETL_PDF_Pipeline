from __future__ import annotations

from pathlib import Path
from typing import Any

from PDF_handle.prod.core.io import ensure_dir, utc_timestamp, write_json
from PDF_handle.prod.core.paths import RUNS_ROOT


def create_run_dir(run_root: Path | None = None) -> Path:
    base = run_root.resolve() if run_root else (RUNS_ROOT / "exploration_review").resolve()
    run_dir = ensure_dir(base / utc_timestamp().replace(":", "-"))
    ensure_dir(run_dir / "graph_clusters")
    return run_dir


def write_exploration_reports(
    *,
    run_dir: Path,
    run_manifest: dict[str, Any],
    clusters: list[dict[str, Any]],
    external_reviews: list[dict[str, Any]],
    reconciliation_report: dict[str, Any],
) -> dict[str, str]:
    run_dir = run_dir.resolve()
    clusters_index = {
        "created_at": utc_timestamp(),
        "cluster_count": len(clusters),
        "cluster_ids": [item["cluster_id"] for item in clusters],
    }
    summary = {
        "created_at": utc_timestamp(),
        "cluster_count": len(clusters),
        "external_review_count": len(external_reviews),
        "classification_counts": reconciliation_report.get("aggregate_counts", {}),
    }

    write_json(run_dir / "run_manifest.json", run_manifest)
    write_json(run_dir / "clusters_index.json", clusters_index)
    for cluster in clusters:
        filename = f"{cluster['cluster_id'].replace(':', '__')}.json"
        write_json(run_dir / "graph_clusters" / filename, cluster)
    write_json(run_dir / "normalized_external_reviews.json", external_reviews)
    write_json(run_dir / "reconciliation_report.json", reconciliation_report)
    write_json(run_dir / "summary_report.json", summary)
    return {
        "run_manifest": str(run_dir / "run_manifest.json"),
        "clusters_index": str(run_dir / "clusters_index.json"),
        "normalized_external_reviews": str(run_dir / "normalized_external_reviews.json"),
        "reconciliation_report": str(run_dir / "reconciliation_report.json"),
        "summary_report": str(run_dir / "summary_report.json"),
        "graph_clusters_dir": str(run_dir / "graph_clusters"),
    }
