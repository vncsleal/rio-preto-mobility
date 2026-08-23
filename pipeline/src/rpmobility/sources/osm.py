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
