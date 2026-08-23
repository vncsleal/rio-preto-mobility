"""Generic ArcGIS REST client for the city's public server.

Handles service discovery, paginated queries (maxRecordCount) and GeoJSON
export. No auth, no SDK — plain HTTP against
https://sig.riopreto.sp.gov.br/server/rest/services
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from ..config import ARCGIS_BASE

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "rio-preto-mobility/0.1 (civic research)"


@dataclass(frozen=True)
class LayerRef:
    service: str
    layer_id: int
    name: str
    max_record_count: int
    geom_type: str


def _url(*parts: str) -> str:
    return f"{ARCGIS_BASE}/{'/'.join(parts)}"


def _service_url(service: str) -> str:
    """Accept 'Folder/Name', 'Folder/Name/MapServer' or '.../FeatureServer'."""
    if not service.endswith(("MapServer", "FeatureServer")):
        service = f"{service}/MapServer"
    return _url(service)


def list_folders() -> list[str]:
    r = SESSION.get(_url(), params={"f": "pjson"}, timeout=30)
    r.raise_for_status()
    return r.json().get("folders", [])


def list_services(folder: str | None = None) -> list[str]:
    r = SESSION.get(_url(*( [folder] if folder else [] )), params={"f": "pjson"}, timeout=30)
    r.raise_for_status()
    return [s["name"] for s in r.json().get("services", [])]


def describe_layer(service: str, layer_id: int) -> LayerRef:
    r = SESSION.get(_service_url(service), params={"f": "pjson"}, timeout=30)
    r.raise_for_status()
    svc = r.json()
    if "error" in svc:
        raise RuntimeError(f"service {service}: {svc['error']}")
    meta = next((l for l in svc.get("layers", []) if l.get("id") == layer_id), None)
    if meta is None:
        raise RuntimeError(f"layer {layer_id} not found in {service}")
    return LayerRef(
        service=service,
        layer_id=layer_id,
        name=meta.get("name", "?"),
        max_record_count=int(svc.get("maxRecordCount") or 1000),
        geom_type=str(svc.get("geometryType") or (meta.get("subLayerIds") and "group") or ""),
    )


def _esri_geometry_to_geojson(g: dict) -> dict | None:
    """Convert Esri JSON geometry (rings/paths/point) to GeoJSON."""
    if not g:
        return None
    if "x" in g:
        return {"type": "Point", "coordinates": [g["x"], g["y"]]}
    if "rings" in g:
        rings = []
        for ring in g["rings"]:
            pts = [[p[0], p[1]] for p in ring]
            if pts and pts[0] != pts[-1]:
                pts.append(pts[0])
            rings.append(pts)
        return {"type": "Polygon", "coordinates": rings}
    if "paths" in g:
        paths = [[[p[0], p[1]] for p in path] for path in g["paths"]]
        if len(paths) == 1:
            return {"type": "LineString", "coordinates": paths[0]}
        return {"type": "MultiLineString", "coordinates": paths}
    return None


def fetch_layer_geojson(
    service: str,
    layer_id: int,
    out_sr: int = 4326,
    sleep_between_pages: float = 0.4,
) -> dict:
    """Fetch every feature of a layer as a GeoJSON FeatureCollection (EPSG:4326).

    Tries f=geojson first; falls back to native f=json + local conversion,
    which some layers require ("Failed to execute query").
    """
    ref = describe_layer(service, layer_id)
    features: list[dict] = []
    offset = 0
    use_esri_json = False

    while True:
        fmt = "json" if use_esri_json else "geojson"
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": out_sr,
            "resultOffset": offset,
            "resultRecordCount": ref.max_record_count,
            "f": fmt,
        }
        r = SESSION.get(
            _service_url(service) + f"/{layer_id}/query", params=params, timeout=120
        )
        r.raise_for_status()
        page = r.json()
        if "error" in page and not use_esri_json:
            use_esri_json = True
            offset = 0
            features.clear()
            continue
        if "error" in page:
            raise RuntimeError(f"query {service}/{layer_id} @{offset}: {page['error']}")

        batch = page.get("features", [])
        if use_esri_json:
            for f in batch:
                geom = _esri_geometry_to_geojson(f.get("geometry"))
                features.append({"type": "Feature", "properties": f.get("attributes", {}), "geometry": geom})
        else:
            features.extend(batch)

        if len(batch) < ref.max_record_count and not page.get("exceededTransferLimit"):
            break
        offset += len(batch)
        if not batch:
            break
        time.sleep(sleep_between_pages)

    fc = {"type": "FeatureCollection", "features": features}
    if use_esri_json:
        # drop null-geometry leftovers so downstream geopandas stays happy
        fc["features"] = [f for f in features if f["geometry"] is not None]
    return fc
