"""Publish helpers — metrics envelope + optional tippecanoe tiling."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def write_metrics(out_dir: Path, metrics: dict) -> Path:
    """Metrics are consumed by apps/web after runtime Zod validation."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "metrics.json"
    target.write_text(
        __import__("json").dumps(metrics, ensure_ascii=False, sort_keys=True, indent=1),
        encoding="utf-8",
    )
    return target


def geojson_to_pmtiles(geojson_path: Path, out_path: Path, layer_name: str) -> Path | None:
    """Convert via tippecanoe + pmtiles if available; else return None (GeoJSON fallback)."""
    tip = shutil.which("tippecanoe")
    pmtiles = shutil.which("pmtiles")
    if not (tip and pmtiles):
        print(f"[publish] tippecanoe/pmtiles not found — serving GeoJSON for {layer_name}")
        return None
    mbtiles = out_path.with_suffix(".mbtiles")
    subprocess.run(
        [
            tip,
            "-o",
            str(mbtiles),
            "-l",
            layer_name,
            "--force",
            "--simplification=10",
            str(geojson_path),
        ],
        check=True,
    )
    subprocess.run([pmtiles, "convert", str(mbtiles), str(out_path)], check=True)
    mbtiles.unlink()
    return out_path
