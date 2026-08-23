"""Weekly snapshot orchestrator.

Fetches every tracked ArcGIS layer into data/raw/snapshots/<date>/,
refreshes the `latest` pointer, writes per-layer meta (checksum) and
emits a diff report vs the previous snapshot. Zero CI involvement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .config import LATEST, SNAPSHOTS, geojson_checksum, write_json
from .sources.arcgis import fetch_layer_geojson
from .sources.targets import HEAVY_LAYERS, TRACKED_LAYERS


def diff_summary(old: dict | None, new: dict, old_ck: str | None, new_ck: str) -> dict:
    if old is None:
        return {"changed": True, "reason": "first snapshot", "checksum": new_ck}
    if old_ck == new_ck:
        return {"changed": False, "checksum": new_ck}
    old_ids = {json.dumps(f["properties"], sort_keys=True) for f in old["features"]}
    new_ids = {json.dumps(f["properties"], sort_keys=True) for f in new["features"]}
    return {
        "changed": True,
        "added": len(new_ids - old_ids),
        "removed": len(old_ids - new_ids),
        "checksumFrom": old_ck,
        "checksumTo": new_ck,
    }


def run_snapshot(
    date: str | None = None, heavy: bool = False, only: tuple[str, ...] = ()
) -> Path:
    date = date or dt.date.today().isoformat()
    out_dir = SNAPSHOTS / date
    out_dir.mkdir(parents=True, exist_ok=True)

    layers = TRACKED_LAYERS + HEAVY_LAYERS if heavy else TRACKED_LAYERS
    if only:
        wanted = set(only)
        unknown = wanted - {t.slug for t in layers}
        if unknown:
            raise SystemExit(f"unknown layers: {', '.join(sorted(unknown))}")
        layers = tuple(t for t in layers if t.slug in wanted)
    report_path = out_dir / "report.json"
    # partial runs (--only) must not erase entries from earlier runs same-day
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text())
            report.setdefault("date", date)
            report.setdefault("layers", {})
        except json.JSONDecodeError:
            report = {"date": date, "layers": {}}
    else:
        report = {"date": date, "layers": {}}
    prev_dir = LATEST if (LATEST.exists() and LATEST.resolve() != out_dir.resolve()) else None

    for t in layers:
        print(f"→ {t.slug}: fetching {t.service}/{t.layer_id} …", flush=True)
        try:
            fc = fetch_layer_geojson(t.service, t.layer_id)
        except Exception as exc:  # noqa: BLE001 — keep going on one bad layer
            print(f"  !! failed: {exc}", file=sys.stderr)
            report["layers"][t.slug] = {"ok": False, "error": str(exc)}
            continue

        ck = geojson_checksum(fc)
        write_json(out_dir / f"{t.slug}.geojson", fc)
        write_json(
            out_dir / f"{t.slug}.meta.json",
            {
                "service": t.service,
                "layerId": t.layer_id,
                "name": t.slug,
                "fetchedAt": dt.datetime.now(dt.UTC).isoformat(),
                "featureCount": len(fc["features"]),
                "crs": "EPSG:4326",
                "checksum": ck,
            },
        )

        old_fc = old_ck = None
        if prev_dir is not None:
            p = prev_dir / f"{t.slug}.geojson"
            if p.exists():
                old_fc = json.loads(p.read_text())
                old_ck = geojson_checksum(old_fc)

        summary = diff_summary(old_fc, fc, old_ck, ck)
        summary.update(featureCount=len(fc["features"]))
        report["layers"][t.slug] = {"ok": True, **summary}

        flag = "" if summary["changed"] else " (unchanged)"
        print(f"  ok: {len(fc['features'])} features{flag}")

    write_json(report_path, report)

    # refresh latest pointer (symlink-free copy keeps Windows/CI simple)
    if LATEST.exists() or LATEST.is_symlink():
        import shutil

        shutil.rmtree(LATEST) if LATEST.is_dir() and not LATEST.is_symlink() else LATEST.unlink()
    LATEST.symlink_to(out_dir.name, target_is_directory=True)

    changed = [k for k, v in report["layers"].items() if v.get("changed")]
    print(f"\nsnapshot {date} done — changed layers: {', '.join(changed) or 'none'}")
    return out_dir


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=None, help="override snapshot date (ISO)")
    ap.add_argument(
        "--heavy", action="store_true", help="also fetch slow/huge layers (zoneamento, logradouros)"
    )
    ap.add_argument(
        "--only",
        nargs="+",
        default=(),
        help="fetch only these slugs (must be in the selected layer set)",
    )
    args = ap.parse_args()
    run_snapshot(args.date, heavy=args.heavy, only=args.only)
