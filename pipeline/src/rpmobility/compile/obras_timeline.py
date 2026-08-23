"""Analysis 3 — obras timeline: prometido × entregue.

Scans every dated snapshot under data/raw/snapshots/, builds the current
inventory of tracked layers and the event list (diffs between consecutive
snapshots). With a single snapshot the inventory is real and events are
empty; the timeline fills in as the weekly launchd job commits more.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from ..config import SNAPSHOTS, WEB_PUBLIC_DATA, write_json
from ..sources.targets import TRACKED_LAYERS

_DESC = {t.slug: t.description for t in TRACKED_LAYERS}


def _load_meta(snapshot_dir: Path, slug: str) -> dict | None:
    p = snapshot_dir / f"{slug}.meta.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _count_property_diffs(a_path: Path, b_path: Path) -> tuple[int, int]:
    """Added/removed feature counts by comparing property sets (geometry-agnostic)."""
    try:
        a = {json.dumps(f["properties"], sort_keys=True) for f in json.loads(a_path.read_text())["features"]}
        b = {json.dumps(f["properties"], sort_keys=True) for f in json.loads(b_path.read_text())["features"]}
        return len(b - a), len(a - b)
    except Exception:  # noqa: BLE001 — a broken file must never kill the report
        return 0, 0


def compile_timeline(snapshots_dir: Path, out_dir: Path) -> dict:
    date_dirs = sorted(
        d for d in snapshots_dir.iterdir()
        if d.is_dir() and not d.is_symlink() and d.name != "latest"
    )
    if not date_dirs:
        raise SystemExit(f"no snapshots found in {snapshots_dir}")

    newest = date_dirs[-1]

    # ---- inventory from the newest snapshot
    layers = []
    slugs_seen: set[str] = set()
    for meta_file in sorted(newest.glob("*.meta.json")):
        meta = json.loads(meta_file.read_text())
        slug = meta["name"]
        if slug in slugs_seen:
            continue
        slugs_seen.add(slug)
        # stable since: walk back while checksum stays identical
        stable_since = newest.name
        for older in reversed(date_dirs[:-1]):
            om = _load_meta(older, slug)
            if om and om.get("checksum") == meta.get("checksum"):
                stable_since = older.name
            else:
                break
        layers.append(
            {
                "slug": slug,
                "description": _DESC.get(slug, ""),
                "service": meta.get("service", ""),
                "featureCount": int(meta.get("featureCount", 0)),
                "lastChecked": meta.get("fetchedAt"),
                "stableSince": stable_since,
                "checksum": meta.get("checksum", ""),
            }
        )

    # ---- events between consecutive snapshots
    events = []
    for prev, nxt in zip(date_dirs, date_dirs[1:]):
        for meta_file in sorted(nxt.glob("*.meta.json")):
            meta = json.loads(meta_file.read_text())
            slug = meta["name"]
            old_meta = _load_meta(prev, slug)
            if old_meta is None:
                events.append(
                    {
                        "slug": slug,
                        "description": _DESC.get(slug, ""),
                        "from": prev.name,
                        "to": nxt.name,
                        "added": 0,
                        "removed": 0,
                        "checksumFrom": "",
                        "checksumTo": meta.get("checksum", ""),
                    }
                )
                continue
            if old_meta.get("checksum") == meta.get("checksum"):
                continue
            added, removed = _count_property_diffs(
                prev / f"{slug}.geojson", nxt / f"{slug}.geojson"
            )
            events.append(
                {
                    "slug": slug,
                    "description": _DESC.get(slug, ""),
                    "from": prev.name,
                    "to": nxt.name,
                    "added": added,
                    "removed": removed,
                    "checksumFrom": old_meta.get("checksum", ""),
                    "checksumTo": meta.get("checksum", ""),
                }
            )

    result = {
        "analysis": "obras-timeline",
        "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
        "snapshotsAnalyzed": len(date_dirs),
        "layers": layers,
        "events": events,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "metrics.json", result)
    print(
        f"obras timeline -> {len(layers)} camadas | {len(date_dirs)} fotografias | "
        f"{len(events)} eventos registrados"
    )
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshots", type=Path, default=SNAPSHOTS)
    ap.add_argument("--out", type=Path, default=WEB_PUBLIC_DATA / "obras")
    args = ap.parse_args()
    compile_timeline(args.snapshots, args.out)
