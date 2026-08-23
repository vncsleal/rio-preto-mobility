"""OpenStreetMap extracts via Overpass (no heavy deps required)."""

from __future__ import annotations

import time

import requests

from ..config import OSM_RELATION_ID

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "rio-preto-mobility/0.1 (civic research)"

def _post_with_retry(query: str, attempts: int = 3) -> dict:
    for i in range(attempts):
        try:
            r = SESSION.post(OVERPASS_URL, data={"data": query}, timeout=300)
            r.raise_for_status()
            return r.json()
        except Exception:  # noqa: BLE001
            if i == attempts - 1:
                raise
            time.sleep(5 * (i + 1))
    raise RuntimeError("unreachable")


def fetch_cycleways_geojson() -> dict:
    """All cycle infrastructure in the municipality as GeoJSON (osm2geojson-free).

    Uses Overpass `out geom` so geometry comes inline — no conversion lib needed.
    """
    query = f"""
    [out:json][timeout:300];
    relation({OSM_RELATION_ID});map_to_area->.a;
    (
      way["highway"="cycleway"](area.a);
      way["cycleway"]["cycleway"!~"no|separate"](area.a);
      way["highway"~"path|footway"]["bicycle"="designated"](area.a);
    );
    out tags geom;
    """
    data = _post_with_retry(query)
    features = []
    for el in data.get("elements", []):
        if el.get("type") != "way" or "geometry" not in el:
            continue
        coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
        props = dict(el.get("tags", {}))
        props["osm_id"] = el["id"]
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def fetch_bus_stops_geojson(out_path) -> dict:
    """Bus stops/platforms mapped in OSM, cached to out_path (pré-GTFS proxy).

    Covers highway=bus_stop and public_transport=platform with bus=yes.
    Ways come back as their center point — good enough for 400 m buffers.
    """
    from pathlib import Path

    out_path = Path(out_path)
    if out_path.exists():
        import json

        return json.loads(out_path.read_text())

    query = f"""
    [out:json][timeout:300];
    relation({OSM_RELATION_ID});map_to_area->.a;
    (
      nwr["highway"="bus_stop"](area.a);
      nwr["public_transport"="platform"]["bus"="yes"](area.a);
    );
    out tags center;
    """
    data = _post_with_retry(query)

    features = []
    seen_ids: set[int] = set()
    for el in data.get("elements", []):
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None or el["id"] in seen_ids:
            continue
        seen_ids.add(el["id"])
        tags = el.get("tags", {})
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "osm_id": el["id"],
                    "name": tags.get("name", ""),
                    "source_tag": "highway" if tags.get("highway") == "bus_stop" else "platform",
                },
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
        )
    fc = {"type": "FeatureCollection", "features": features}
    from ..config import write_json

    write_json(out_path, fc)
    return fc
