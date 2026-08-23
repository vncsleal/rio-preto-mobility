"""Publish helpers — metrics envelope + tippecanoe → PMTiles tiling."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

# heavy layers worth serving as vector tiles (name -> tippecanoe options)
TILE_TARGETS: dict[str, dict] = {
    "quadras": {"layer": "quadras", "zooms": ["-Z10", "-z15"]},
    "setores_censitarios": {"layer": "setores", "zooms": ["-Z8", "-z14"]},
    "logradouros": {
        "layer": "logradouros",
        "zooms": ["-Z10", "-z15", "--drop-densest-as-needed"],
    },
}


def write_metrics(out_dir: Path, metrics: dict) -> Path:
    """Metrics are consumed by apps/web after runtime Zod validation."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "metrics.json"
    target.write_text(
        json.dumps(metrics, ensure_ascii=False, sort_keys=True, indent=1),
        encoding="utf-8",
    )
    return target


def geojson_to_pmtiles(geojson_path: Path, out_path: Path, layer_name: str,
                       zooms: list[str] | None = None) -> Path | None:
    """Convert via tippecanoe + pmtiles if available; else return None (GeoJSON fallback)."""
    tip = shutil.which("tippecanoe")
    pmtiles = shutil.which("pmtiles")
    if not (tip and pmtiles):
        print(f"[publish] tippecanoe/pmtiles not found — serving GeoJSON for {layer_name}")
        return None
    mbtiles = out_path.with_suffix(".mbtiles")
    cmd = [
        tip,
        "-o",
        str(mbtiles),
        "-l",
        layer_name,
        "--force",
        "--simplification=10",
        *(zooms or []),
        str(geojson_path),
    ]
    subprocess.run(cmd, check=True)
    subprocess.run([pmtiles, "convert", str(mbtiles), str(out_path)], check=True)
    mbtiles.unlink()
    return out_path


def build_tiles(snapshots_latest: Path, out_dir: Path,
                only: tuple[str, ...] = ()) -> Path:
    """Convert TILE_TARGETS found in the latest snapshot; write manifest.json."""
    if not shutil.which("tippecanoe") or not shutil.which("pmtiles"):
        raise SystemExit(
            "tippecanoe/pmtiles ausentes — instale com: brew install tippecanoe pmtiles"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"generatedAt": "", "tiles": {}}
    for slug, cfg in TILE_TARGETS.items():
        if only and slug not in only:
            continue
        src = snapshots_latest / f"{slug}.geojson"
        if not src.exists():
            print(f"[tiles] {slug}: fonte ausente ({src}) — pulando")
            continue
        dest = out_dir / f"{slug}.pmtiles"
        print(f"[tiles] {slug} -> {dest.name} …")
        result = geojson_to_pmtiles(src, dest, cfg["layer"], cfg["zooms"])
        if result is not None:
            import datetime as dt

            manifest["tiles"][slug] = {
                "url": f"/data/tiles/{dest.name}",
                "layer": cfg["layer"],
                "bytes": dest.stat().st_size,
                "extractDate": src.resolve().parent.name,
                "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
            }
    import datetime as dt

    manifest["generatedAt"] = dt.datetime.now(dt.UTC).isoformat()
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return out_dir / "manifest.json"


if __name__ == "__main__":
    import argparse

    from ..config import LATEST, WEB_PUBLIC_DATA

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--latest", type=Path, default=LATEST)
    ap.add_argument("--out", type=Path, default=WEB_PUBLIC_DATA.parent / "data" / "tiles")
    ap.add_argument("--only", nargs="*", default=())
    args = ap.parse_args()
    build_tiles(args.latest, args.out, tuple(args.only))
