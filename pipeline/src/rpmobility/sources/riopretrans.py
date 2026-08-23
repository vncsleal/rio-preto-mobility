"""RioPretrans official bus stops — from the public lines map.

The concessionaire's map site (linhasriopreto.riopretrans.com.br/mapa)
exposes an unauthenticated AJAX endpoint (`mapa/pontosproximos`) returning
official stops near a coordinate: code, address, lat/lon and the itineraries
served. This is the operator's own data — better than OSM, no GTFS required.

Harvest strategy: query a ~0.65 km-step grid over the union of URBAN census
sectors (IBGE malha), which covers the urban perimeter AND the district
villages while skipping empty farmland. Endpoint radius is ~500 m, so the
grid overlaps fully. Polite: 0.3 s between requests, identifying UA.

This is a stopgap until the GTFS requested in docs/lai-gtfs.md lands —
the harvester stays useful as a cross-check even then.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import time
from pathlib import Path

import requests

from ..config import REPO_ROOT, WORKING_CRS, write_json

MAP_BASE = "https://linhasriopreto.riopretrans.com.br/mapa"
PONTOS_URL = f"{MAP_BASE}/mapa/pontosproximos"
STEPS_KM = 0.65
SLEEP_S = 0.3

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "rio-preto-mobility/0.1 (civic research)",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{MAP_BASE}/",
    }
)


def _bootstrap_session() -> None:
    """Grab a PHP session cookie like a browser visit would."""
    try:
        SESSION.get(f"{MAP_BASE}/", timeout=20)
    except requests.RequestException:
        pass  # endpoint works even if the homepage hiccups


def nearby_stops(lat: float, lon: float) -> list[dict]:
    r = SESSION.post(PONTOS_URL, data={"lat": f"{lat}", "lon": f"{lon}"}, timeout=30)
    r.raise_for_status()
    return r.json().get("pontos", [])


def urban_seeds(sector_gpkg: Path) -> list[tuple[float, float]]:
    """Grid seeds INSIDE urban sector polygons (city + district villages).

    Point-in-polygon against the dissolved union — bbox grids over the
    sectors' extents cover 3.5× the area and mostly query empty farmland.
    """
    import geopandas as gpd
    from shapely.geometry import Point
    from shapely.prepared import prep

    from ..config import MUNICIPALITY_GEOCODE

    setores = gpd.read_file(sector_gpkg)
    setores = setores[setores["CD_MUN"].astype(str) == MUNICIPALITY_GEOCODE]
    situacao = setores["SITUACAO"].astype(str).str.upper()
    urban = setores[situacao.str.startswith("URBANA")].to_crs("EPSG:4326")
    if urban.empty:
        urban = setores.to_crs("EPSG:4326")

    union = prep(urban.union_all())
    minx, miny, maxx, maxy = urban.total_bounds

    km_lat = STEPS_KM / 111.32
    seeds: list[tuple[float, float]] = []
    lat = miny
    while lat <= maxy:
        km_lon = STEPS_KM / (111.32 * math.cos(math.radians(lat)))
        lon = minx
        while lon <= maxx:
            if union.covers(Point(lon, lat)):
                seeds.append((round(lat, 6), round(lon, 6)))
            lon += km_lon
        lat += km_lat
    return seeds


def harvest(sector_gpkg: Path, out_path: Path, sleep: float = SLEEP_S) -> dict:
    """Grid-query pontosproximos; dedupe by stop id; resumable via sidecar state."""
    if out_path.exists():
        return json.loads(out_path.read_text())

    state_path = out_path.with_suffix(".state.json")
    state: dict = {"visited": [], "stops": {}}
    if state_path.exists():
        state = json.loads(state_path.read_text())
        print(f"riopretrans: retomando — {len(state['visited'])} seeds já visitados")

    _bootstrap_session()
    seeds = urban_seeds(sector_gpkg)
    todo = [s for s in seeds if [s[0], s[1]] not in state["visited"]]
    print(f"riopretrans: {len(todo)}/{len(seeds)} seeds a consultar (grade {STEPS_KM} km) …")

    def _persist():
        write_json(state_path, state)

    errors = 0
    for n, (lat, lon) in enumerate(todo, 1):
        if n % 25 == 0 or n == len(todo):
            print(f"  {n}/{len(todo)} | {len(state['stops'])} paradas únicas", flush=True)
            _persist()
        try:
            stops = nearby_stops(lat, lon)
        except Exception:  # noqa: BLE001 — one failed seed never kills the harvest
            errors += 1
            time.sleep(sleep * 4)
        else:
            for p in stops:
                sid = str(p.get("id") or p.get("codponto"))
                if sid in state["stops"]:
                    continue
                try:
                    lat_f, lon_f = float(p["lat"]), float(p["lon"])
                except (KeyError, TypeError, ValueError):
                    continue
                if lat_f == 0 and lon_f == 0:
                    continue
                linhas = sorted(
                    {
                        str(i.get("codlinha"))
                        for i in p.get("itinerarios", [])
                        if i.get("codlinha")
                    }
                )
                state["stops"][sid] = {
                    "osm_id": f"riopretrans:{sid}",
                    "name": (p.get("referencia") or "").strip(),
                    "source_tag": "riopretrans",
                    "stop_code": str(p.get("codponto") or ""),
                    "endereco": (p.get("endereco") or "").strip(),
                    "routes": len(linhas),
                    "linhas": linhas,
                    "_lon": lon_f,
                    "_lat": lat_f,
                }
        state["visited"].append([lat, lon])
        time.sleep(sleep)
    _persist()

    features = []
    for props in state["stops"].values():
        lon_f, lat_f = props.pop("_lon"), props.pop("_lat")
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
            }
        )
    fc = {
        "type": "FeatureCollection",
        "features": features,
        "harvestedAt": dt.datetime.now(dt.UTC).isoformat(),
        "seeds": len(seeds),
        "seedErrors": errors,
    }
    write_json(out_path, fc)
    state_path.unlink(missing_ok=True)
    print(f"riopretrans: {len(features)} paradas oficiais ({errors} seeds falharam)")
    return fc


def stops_geojson(out_path: Path | None = None) -> dict:
    """Cached accessor used by the compiler."""
    out_path = out_path or (REPO_ROOT / "data" / "raw" / "riopretrans" / "stops.geojson")
    if not out_path.exists():
        from ..sources.ibge import malha_sp_setores

        harvest(malha_sp_setores(), out_path)
    return json.loads(out_path.read_text())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--setores", type=Path, default=REPO_ROOT / "data" / "raw" / "ibge" / "SP_setores_CD2022.gpkg")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "raw" / "riopretrans" / "stops.geojson")
    ap.add_argument("--sleep", type=float, default=SLEEP_S)
    args = ap.parse_args()
    harvest(args.setores, args.out, args.sleep)
