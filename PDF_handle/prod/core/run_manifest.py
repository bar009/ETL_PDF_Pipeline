"""The canonical run-manifest shape and builder (systemic plan WS8).

Every run should leave one small JSON file that debugging can start from:
what ran, on what inputs, with what config, which steps happened, what was
produced, what it cost, and what went wrong. The committed shape contract
lives in ``data/schemas/run_manifest.schema.json``.

Usage:

    manifest = RunManifest(tool="smoke_fixture", inputs={...}, config={...})
    manifest.add_step("extract", ok=True, counts={"books": 1})
    manifest.add_provider_usage(provider_result)
    manifest.add_output(path)
    manifest.finish()
    manifest.write(report_dir)          # -> <report_dir>/run_manifest.json
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from PDF_handle.prod.core.io import utc_timestamp, write_json
from PDF_handle.prod.core.runtime import timestamp_slug

MANIFEST_VERSION = 1
MANIFEST_FILENAME = "run_manifest.json"


class RunManifest:
    def __init__(
        self,
        *,
        tool: str,
        inputs: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.tool = tool
        self.run_id = f"{tool}-{timestamp_slug()}"
        self.started_at = utc_timestamp()
        self.inputs = dict(inputs or {})
        self.config = dict(config or {})
        self.steps: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.outputs: list[str] = []
        self.provider_usage: list[dict[str, Any]] = []
        self.finished_at: str | None = None
        self.duration_seconds: float | None = None
        self._perf_start = time.perf_counter()

    def add_step(
        self,
        name: str,
        *,
        ok: bool,
        detail: str = "",
        counts: dict[str, int] | None = None,
    ) -> bool:
        step: dict[str, Any] = {"name": name, "ok": ok}
        if detail:
            step["detail"] = detail
        if counts:
            step["counts"] = dict(counts)
        self.steps.append(step)
        if not ok:
            self.errors.append(f"{name}: {detail}" if detail else name)
        return ok

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_output(self, path: Path | str) -> None:
        self.outputs.append(str(path))

    def add_provider_usage(self, result: Any) -> None:
        """Record a ProviderResult (or compatible object/dict) summary."""
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        self.provider_usage.append(
            {
                "provider": payload.get("provider"),
                "model": payload.get("model"),
                "transport": payload.get("transport"),
                "usage_metadata": payload.get("usage_metadata"),
                "duration_seconds": payload.get("duration_seconds"),
                "error_kind": payload.get("error_kind"),
            }
        )

    @property
    def counts(self) -> dict[str, int]:
        return {
            "steps": len(self.steps),
            "steps_failed": sum(1 for step in self.steps if not step["ok"]),
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "outputs": len(self.outputs),
            "provider_calls": len(self.provider_usage),
        }

    @property
    def ok(self) -> bool:
        return not self.errors

    def finish(self) -> "RunManifest":
        if self.finished_at is None:
            self.finished_at = utc_timestamp()
            self.duration_seconds = round(time.perf_counter() - self._perf_start, 6)
        return self

    def to_dict(self) -> dict[str, Any]:
        self.finish()
        return {
            "manifest_version": MANIFEST_VERSION,
            "run_id": self.run_id,
            "tool": self.tool,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "inputs": self.inputs,
            "config": self.config,
            "steps": self.steps,
            "counts": self.counts,
            "warnings": self.warnings,
            "errors": self.errors,
            "outputs": self.outputs,
            "provider_usage": self.provider_usage,
            "ok": self.ok,
        }

    def write(self, report_dir: Path) -> Path:
        path = Path(report_dir) / MANIFEST_FILENAME
        write_json(path, self.to_dict())
        return path
