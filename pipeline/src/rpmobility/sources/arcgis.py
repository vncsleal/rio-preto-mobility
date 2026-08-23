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
    object_id_field: str = "OBJECTID"


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
    # layer-level json carries the authoritative objectIdField
    rl = SESSION.get(
        _service_url(service) + f"/{layer_id}", params={"f": "pjson"}, timeout=30
    )
    layer_meta = {}
    try:
        rl.raise_for_status()
        layer_meta = rl.json()
        if "error" in layer_meta:
            layer_meta = {}
    except Exception:  # noqa: BLE001 — descriptive metadata only
        layer_meta = {}

    oid_field = str(
        layer_meta.get("objectIdField")
        or next(
            (f["name"] for f in layer_meta.get("fields", []) if f.get("type") == "esriFieldTypeOID"),
            None,
        )
        or "OBJECTID"
    )
    return LayerRef(
        service=service,
        layer_id=layer_id,
        name=meta.get("name", "?"),
        max_record_count=int(svc.get("maxRecordCount") or 1000),
        geom_type=str(svc.get("geometryType") or (meta.get("subLayerIds") and "group") or ""),
        object_id_field=oid_field,
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
    which some layers require ("Failed to execute query"). Layers that
    reject resultOffset AND resultRecordCount (locked-down servers) fall
    through to OID-window paging: `where OID > lo and OID <= hi` with no
    record-count parameter, advancing fixed windows with skip-ahead.
    """
    ref = describe_layer(service, layer_id)
    features: list[dict] = []
    offset = 0
    last_oid: int | None = None
    use_esri_json = False
    mode = "offset"  # offset -> keyset -> window

    WINDOW = 800
    win_lo: int | None = None
    empty_windows = 0
    high_water = 0

    def _params() -> dict:
        p = {
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": out_sr,
            "f": "json" if use_esri_json else "geojson",
        }
        if mode == "offset":
            p["where"] = "1=1"
            p["resultOffset"] = offset
            p["resultRecordCount"] = ref.max_record_count
        elif mode == "keyset":
            p["where"] = (
                f"{ref.object_id_field}>{last_oid}" if last_oid is not None else "1=1"
            )
            p["orderByFields"] = ref.object_id_field
            p["resultRecordCount"] = ref.max_record_count
        else:  # window: NO resultRecordCount — this server rejects it
            p["where"] = (
                f"{ref.object_id_field}>{win_lo} AND {ref.object_id_field}<={win_lo + WINDOW}"
                if win_lo is not None
                else f"{ref.object_id_field}>0"
            )
        return p

    while True:
        r = SESSION.get(
            _service_url(service) + f"/{layer_id}/query", params=_params(), timeout=120
        )
        r.raise_for_status()
        page = r.json()
        err = page.get("error")
        if err and not use_esri_json:
            use_esri_json = True
            features.clear()
            continue
        if err and mode == "offset":
            # server rejects resultOffset entirely
            mode = "keyset"
            use_esri_json = True
            features.clear()
            continue
        if err and mode == "keyset":
            # rejects resultRecordCount too — window paging without it
            mode = "window"
            features.clear()
            continue
        if err:
            raise RuntimeError(f"query {service}/{layer_id} @{offset}: {err}")

        batch = page.get("features", [])
        if use_esri_json:
            for f in batch:
                geom = _esri_geometry_to_geojson(f.get("geometry"))
                features.append({"type": "Feature", "properties": f.get("attributes", {}), "geometry": geom})
        else:
            features.extend(batch)

        if mode == "offset":
            done = len(batch) < ref.max_record_count and not page.get("exceededTransferLimit")
            if done:
                break
            offset += len(batch)
            time.sleep(sleep_between_pages)
            continue

        oids = [
            int(f["attributes"].get(ref.object_id_field) or 0) for f in batch
        ]

        if mode == "keyset":
            new_last = max(oids) if oids else None
            if new_last is None or new_last == last_oid:
                break  # no progress — avoid infinite loop
            last_oid = new_last
        else:  # window paging: unique OIDs ⇒ ≤WINDOW rows per request
            if batch:
                empty_windows = 0
                high_water = max(high_water, max(oids))
                step = WINDOW
            else:
                empty_windows += 1
                step = WINDOW * (10 ** min(empty_windows, 3))
            win_lo = (win_lo or 0) + step
            if empty_windows >= 3 and win_lo > high_water:
                break
            if not batch and empty_windows == 0:
                break

    fc = {"type": "FeatureCollection", "features": features}
    if use_esri_json:
        # drop null-geometry leftovers so downstream geopandas stays happy
        fc["features"] = [f for f in features if f["geometry"] is not None]
    return fc
