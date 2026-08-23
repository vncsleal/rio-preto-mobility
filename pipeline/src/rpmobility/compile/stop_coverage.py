"""Analysis 4 — cobertura de paradas de ônibus (pré-GTFS).

Population within a straight-line 400 m of any OSM-mapped bus stop, per
bairro, crossed with Censo 2022 income. This is the LAI-free preliminary
version: when GTFS lands (see PLAN.md), swap OSM stops for the official feed
and straight-line buffers for network distances (r5r).

Pure helpers `tercile_means`/`coverage_share` are unit-testable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from ..config import LATEST, REPO_ROOT, WEB_PUBLIC_DATA, WORKING_CRS, write_json
from .common import build_territory_units, municipal_setores
from .access_score import weighted_mean

RADIUS_M = 400.0


def coverage_share(pop_total: int, pop_covered: int) -> float:
    if pop_total <= 0:
        return 0.0
    return round(min(max(pop_covered / pop_total, 0.0), 1.0), 4)


def tercile_means(pairs: list[tuple[float, float]]) -> dict[str, float]:
    """Mean coverage for income terciles. pairs = [(renda, coverageShare), …].

    Bairros without income are ignored; ties at the cut points go to the
    richer tercil (stable sort keeps it deterministic).
    """
    known = sorted((r, c) for r, c in pairs if r is not None)
    n = len(known)
    if n < 3:
        return {}
    cuts = (n // 3, 2 * n // 3)
    groups = {
        "baixa": [c for _, c in known[: cuts[0]]],
        "media": [c for _, c in known[cuts[0] : cuts[1]]],
        "alta": [c for _, c in known[cuts[1] :]],
    }
    return {k: round(sum(v) / len(v), 3) for k, v in groups.items() if v}


def compile_stops(
    bairros_path: Path,
    stops_path: Path,
    out_dir: Path,
    quadras_path: Path | None = None,
) -> dict:
    import geopandas as gpd

    from ..sources.ibge import censo_population_by_setor, censo_renda_by_setor

    units = build_territory_units(bairros_path, quadras_path)
    if units.empty:
        raise SystemExit("no territory units built — check bairros/quadras inputs")

    stops_fc = fetch_stops(stops_path)
    stops = gpd.GeoDataFrame.from_features(stops_fc["features"], crs="EPSG:4326").to_crs(WORKING_CRS)
    print(f"paradas OSM no município: {len(stops)}")

    # ---- census attributes per sector, then per bairro
    pop_by_setor, rel_pop = censo_population_by_setor()
    try:
        renda_by_setor, rel_renda = censo_renda_by_setor()
        censo_release = f"pop:{rel_pop};renda:{rel_renda}"
    except Exception as exc:  # noqa: BLE001 — renda é opcional
        renda_by_setor = {}
        censo_release = f"pop:{rel_pop}"
        print(f"renda indisponível ({exc}) — análise segue sem renda")

    setores = municipal_setores(units)
    pts = setores.copy()
    pts["geometry"] = pts.geometry.representative_point()
    pts["pop"] = pts["CD_SETOR"].map(pop_by_setor).fillna(0).astype(int)
    pts["renda"] = pts["CD_SETOR"].map(lambda cd: (renda_by_setor.get(cd) or {}).get("rendaMedia"))
    pts["resp"] = pts["CD_SETOR"].map(lambda cd: (renda_by_setor.get(cd) or {}).get("responsaveis", 0))

    joined = gpd.sjoin(
        pts[["CD_SETOR", "pop", "renda", "resp", "geometry"]],
        units[["bairro_id", "geometry"]],
        how="inner",
        predicate="within",
    )

    # ---- coverage flag: sector centroid within RADIUS_M of any stop
    stop_buf = stops.buffer(RADIUS_M).union_all()
    joined["covered"] = joined.geometry.within(stop_buf)

    rows = []
    for bid, grp in joined.groupby("bairro_id"):
        pop_total = int(grp["pop"].sum())
        pop_cov = int(grp.loc[grp["covered"], "pop"].sum())
        rows.append(
            {
                "sectorId": bid,
                "bairro": str(units.loc[units["bairro_id"] == bid, "nome_b"].iloc[0] or ""),
                "population": pop_total,
                "meanIncome": weighted_mean(list(zip(grp["renda"], grp["resp"]))),
                "popWithin400m": pop_cov,
                "coverageShare": coverage_share(pop_total, pop_cov),
            }
        )
    # keep unit order stable and include zero-population bairros with share 0
    have = {r["sectorId"] for r in rows}
    for bid in units["bairro_id"]:
        if bid not in have:
            name = str(units.loc[units["bairro_id"] == bid, "nome_b"].iloc[0] or "")
            rows.append(
                {
                    "sectorId": bid,
                    "bairro": name,
                    "population": 0,
                    "meanIncome": None,
                    "popWithin400m": 0,
                    "coverageShare": 0.0,
                }
            )

    pop_total_city = sum(r["population"] for r in rows)
    pop_cov_city = sum(r["popWithin400m"] for r in rows)
    result = {
        "analysis": "stop-coverage",
        "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
        "extractDates": {"osm": "overpass", "censo": censo_release},
        "radiusM": RADIUS_M,
        "summary": {
            "stopsTotal": len(stops),
            "popTotal": pop_total_city,
            "popCoberta": pop_cov_city,
            "coberturaMedia": coverage_share(pop_total_city, pop_cov_city),
            **(
                {"porTercilRenda": tercile_means([(r["meanIncome"], r["coverageShare"]) for r in rows])}
                if renda_by_setor
                else {}
            ),
        },
        "coberturas": rows,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "metrics.json", result)

    # ---- map artifacts: stops + choropleth of coverage
    def _pt_features(gdf):
        feats = []
        gdf_w = gdf.to_crs("EPSG:4326")
        for _, row in gdf_w.iterrows():
            props = {
                k: _finite_or_none(row.get(k))
                for k in ("osm_id", "name", "source_tag")
                if row.get(k) not in (None, "")
            }
            feats.append(
                {
                    "type": "Feature",
                    "properties": props,
                    "geometry": json.loads(json.dumps(row.geometry.__geo_interface__)),
                }
            )
        return feats

    write_json(out_dir / "stops.geojson", {"type": "FeatureCollection", "features": _pt_features(stops)})

    from .common import polygonal

    areas = []
    cov_by_id = {r["sectorId"]: r for r in rows}
    for urow in units.itertuples():
        r = cov_by_id.get(urow.bairro_id)
        if r is None:
            continue
        poly = polygonal(urow.geometry)
        if poly is None:
            continue
        poly_wgs = gpd.GeoSeries([poly], crs=WORKING_CRS).to_crs("EPSG:4326").iloc[0]
        props = {
            "sectorId": r["sectorId"],
            "name": r["bairro"],
            "coverageShare": r["coverageShare"],
            "population": r["population"],
            **({"meanIncome": r["meanIncome"]} if r["meanIncome"] is not None else {}),
        }
        areas.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": json.loads(json.dumps(poly_wgs.__geo_interface__)),
            }
        )
    write_json(out_dir / "areas.geojson", {"type": "FeatureCollection", "features": areas})

    s = result["summary"]
    print(
        f"cobertura -> {s['stopsTotal']} paradas | {s['coberturaMedia']*100:.0f}% da população "
        f"a ≤{int(RADIUS_M)} m | tercis renda: {s.get('porTercilRenda')}"
    )
    return result


def fetch_stops(stops_path: Path) -> dict:
    from ..sources.osm import fetch_bus_stops_geojson

    return fetch_bus_stops_geojson(stops_path)


def _finite_or_none(v):
    import math

    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bairros", type=Path, default=LATEST / "bairros.geojson")
    ap.add_argument("--quadras", type=Path, default=LATEST / "quadras.geojson")
    ap.add_argument("--stops", type=Path, default=REPO_ROOT / "data" / "raw" / "osm" / "stops.geojson")
    ap.add_argument("--out", type=Path, default=WEB_PUBLIC_DATA / "transporte")
    args = ap.parse_args()
    compile_stops(args.bairros, args.stops, args.out, args.quadras)
