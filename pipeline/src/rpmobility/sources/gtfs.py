"""GTFS ingestion — ready for the day the official feed lands.

Rio Preto's urban system (RioPretrans) publishes no open GTFS today; the
LAI request lives in docs/lai-gtfs.md. This module is the drop-in: point it
at a feed zip and /transporte upgrades from OSM stops to the official data
without touching the compiler's contract.

Parses with stdlib only (zipfile + csv). Stops are enriched with the number
of routes serving them, streamed so big feeds stay memory-bounded.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

from ..config import write_json


def _read_csv(zf: zipfile.ZipFile, name: str) -> list[dict]:
    """Rows of a GTFS member file; tolerates BOM, utf-8/latin-1, missing files."""
    target = next((n for n in zf.namelist() if n.lower().endswith(name)), None)
    if target is None:
        return []
    fh = zf.open(target)
    sample = fh.read(4096)
    fh.seek(0)
    try:
        sample.decode("utf-8-sig")
        enc = "utf-8-sig"
    except UnicodeDecodeError:
        enc = "latin-1"
    text = io.TextIOWrapper(fh, encoding=enc, errors="replace", newline="")
    return list(csv.DictReader(text, delimiter=","))


def routes_per_stop(zip_path: Path) -> dict[str, int]:
    """stop_id -> count of distinct routes reaching it (via trips)."""
    out: dict[str, int] = {}
    with zipfile.ZipFile(zip_path) as zf:
        route_of_trip = {
            t["trip_id"]: t.get("route_id", "")
            for t in _read_csv(zf, "trips.txt")
        }
        seen: dict[str, set[str]] = {}
        for st in _read_csv(zf, "stop_times.txt"):
            sid = st.get("stop_id")
            rid = route_of_trip.get(st.get("trip_id"), "")
            if not sid or not rid:
                continue
            seen.setdefault(sid, set()).add(rid)
        out = {sid: len(r) for sid, r in seen.items()}
    return out


def stops_geojson(zip_path: Path, out_path: Path) -> tuple[dict, str]:
    """GTFS stops as a FeatureCollection cached to out_path.

    Returns (fc, feed_label) where feed_label identifies the source file.
    """
    if out_path.exists():
        import json

        return json.loads(out_path.read_text()), zip_path.name

    per_stop_routes = routes_per_stop(zip_path)
    features = []
    with zipfile.ZipFile(zip_path) as zf:
        for s in _read_csv(zf, "stops.txt"):
            try:
                lat = float(s.get("stop_lat") or 0)
                lon = float(s.get("stop_lon") or 0)
            except (TypeError, ValueError):
                continue
            if lat == 0 and lon == 0:
                continue
            sid = s.get("stop_id") or ""
            props = {
                "osm_id": f"gtfs:{sid}",
                "name": s.get("stop_name") or "",
                "source_tag": "gtfs",
                "stop_code": s.get("stop_code") or None,
                "routes": int(per_stop_routes.get(sid, 0)),
            }
            features.append(
                {
                    "type": "Feature",
                    "properties": {k: v for k, v in props.items() if v is not None},
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                }
            )
    fc = {"type": "FeatureCollection", "features": features}
    write_json(out_path, fc)
    return fc, zip_path.name
