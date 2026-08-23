"""
Analysis 2 — 15-minute access score per bairro.

Walk network from OSM (osmnx) + POI categories (saúde, educação, comércio),
isochrone math via pandana. Aggregation unit: official bairro polygons from
the city's ArcGIS (Hosted/Bairros). With --with-censo, population and mean
income (responsável com rendimento, weighted) come from Censo 2022 aggregates
joined via the IBGE malha (CD_SETOR).

Requires the [network] extra: uv pip install -e "pipeline[network]"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

from ..config import REPO_ROOT, WORKING_CRS, write_json

TIME_BUDGET_MIN = 15.0
WALK_SPEED_KMH = 4.5
BUDGET_M = int(TIME_BUDGET_MIN / 60 * WALK_SPEED_KMH * 1000)  # ~1125 m

PLACE = "São José do Rio Preto, São Paulo, Brazil"

POI_CATEGORIES: dict[str, dict] = {
    "educacao": {"amenity": {"school", "kindergarten", "college", "library", "language_school"}},
    "saude": {"amenity": {"hospital", "clinic", "doctors", "pharmacy", "dentist"}},
    "comercio": {"shop": {"supermarket", "greengrocer", "convenience"}},
}
CAP_PER_CATEGORY = 5.0


def weighted_mean(values_weights: list[tuple[float, int]]) -> float | None:
    """Weighted mean of (value, weight) pairs; skips null/non-finite values."""
    num = den = 0.0
    for v, w in values_weights:
        if v is None or w is None or w <= 0:
            continue
        if isinstance(v, float) and not math.isfinite(v):
            continue
        num += v * w
        den += w
    return round(num / den, 2) if den > 0 else None


def _finite_or_none(v):
    """NaN/Inf -> None so artifacts stay strict-JSON."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def attach_census(bairros, pop_by_setor: dict[str, int | None], renda_by_setor: dict[str, dict]):
    """Sum Censo 2022 population + weighted mean income into bairro units.

    `bairros` needs a `bairro_id` column; returns (bairros, matched_sectors).
    Sectors whose centroid falls outside every bairro polygon (rural) are
    naturally dropped by the within-join. Income is weighted by responsáveis
    com rendimento (V06001), the weight IBGE itself uses.
    """
    import geopandas as gpd
    import pandas as pd

    from ..sources.ibge import malha_sp_setores

    gpkg = malha_sp_setores()
    # bbox must be in the file's CRS (4326): transform bounds before reading
    bounds_wgs = tuple(bairros.to_crs("EPSG:4326").total_bounds)
    setores = gpd.read_file(gpkg, bbox=bounds_wgs)
    setores = setores[setores["CD_MUN"].astype(str) == "3549805"].to_crs(WORKING_CRS)
    setores = setores[setores.geometry.notna() & ~setores.geometry.is_empty]
    if setores.empty:
        print("censo: nenhum setor do município na malha — censo fica null")
        return bairros, {}

    pts = setores.copy()
    pts["geometry"] = pts.geometry.representative_point()
    pts["pop"] = pts["CD_SETOR"].map(pop_by_setor).fillna(0).astype(int)
    pts["renda"] = pts["CD_SETOR"].map(
        lambda cd: (renda_by_setor.get(cd) or {}).get("rendaMedia")
    )
    pts["resp"] = pts["CD_SETOR"].map(
        lambda cd: (renda_by_setor.get(cd) or {}).get("responsaveis", 0)
    )

    joined = gpd.sjoin(
        pts[["CD_SETOR", "pop", "renda", "resp", "geometry"]],
        bairros[["bairro_id", "geometry"]],
        how="inner",
        predicate="within",
    )
    pop_sums = joined.groupby("bairro_id")["pop"].sum()

    renda_means = {
        bid: weighted_mean(list(zip(grp["renda"], grp["resp"])))
        for bid, grp in joined.groupby("bairro_id")
    }

    bairros = bairros.copy()
    bairros["population"] = bairros["bairro_id"].map(pop_sums).fillna(0).astype(int)
    # object dtype on purpose: a [float|None] list would upcast to float64
    # and silently turn None into NaN
    bairros["meanIncome"] = pd.Series(
        [renda_means.get(b) for b in bairros["bairro_id"]],
        index=bairros.index,
        dtype=object,
    )
    print(f"censo: {len(setores)} setores -> população/renda em {len(pop_sums)} bairros")
    return bairros, len(joined.drop_duplicates("CD_SETOR"))


def _graph_cache() -> Path:
    return REPO_ROOT / "data" / "raw" / "osm" / "walk.graphml"


def load_walk_network():
    """Cached city-wide walk graph as a pandana Network in WORKING_CRS."""
    import osmnx as ox
    import pandana as pdna

    cache = _graph_cache()
    if cache.exists():
        G = ox.load_graphml(cache)
    else:
        G = ox.graph_from_place(PLACE, network_type="walk")
        ox.save_graphml(G, cache)
    G = ox.project_graph(G, to_crs=WORKING_CRS)

    try:
        nodes, edges = ox.convert.graph_to_gdfs(G, nodes=True, edges=True)
    except AttributeError:  # osmnx < 2.0
        nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

    if "u" not in edges.columns:  # osmnx >= 2.0 keeps u/v in the MultiIndex
        net = pdna.Network(
            nodes.geometry.x,
            nodes.geometry.y,
            edges.index.get_level_values("u").astype(int),
            edges.index.get_level_values("v").astype(int),
            edges[["length"]].reset_index(drop=True),
        )
    else:
        net = pdna.Network(nodes.geometry.x, nodes.geometry.y, edges["u"], edges["v"], edges[["length"]])
    net.precompute(BUDGET_M + 500)
    return net


def fetch_pois_geojson(out_path: Path) -> dict:
    """Pull all category POIs from Overpass (cached to out_path)."""
    if out_path.exists():
        return json.loads(out_path.read_text())

    from ..sources.osm import _post_with_retry  # noqa: PLC0415
    from ..config import OSM_RELATION_ID  # noqa: PLC0415

    filters = []
    for cat, spec in POI_CATEGORIES.items():
        for key, values in spec.items():
            for v in values:
                filters.append(f'node["{key}"="{v}"](area.a);')
                filters.append(f'way["{key}"="{v}"](area.a);')
    joined = "\n".join(filters)

    query = (
        "[out:json][timeout:300];\n"
        f"relation({OSM_RELATION_ID});map_to_area->.a;\n(\n"
        f"{joined}\n"
        ");\nout tags center;\n"
    )
    data = _post_with_retry(query)

    features = []
    for el in data.get("elements", []):
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        tags = el.get("tags", {})
        category = next(
            (
                c
                for c, spec in POI_CATEGORIES.items()
                if tags.get(next(iter(spec))) in next(iter(spec.values()))
            ),
            None,
        )
        if category is None:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {"category": category, "osm_id": el["id"], "name": tags.get("name", "")},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
        )
    fc = {"type": "FeatureCollection", "features": features}
    write_json(out_path, fc)
    return fc


def compile_access(
    bairros_path: Path,
    pois_path: Path,
    out_dir: Path,
    quadras_path: Path | None = None,
    with_censo: bool = False,
) -> dict:
    import geopandas as gpd

    net = load_walk_network()

    pois_fc = fetch_pois_geojson(pois_path)
    pois = gpd.GeoDataFrame.from_features(pois_fc["features"], crs="EPSG:4326").to_crs(WORKING_CRS)

    # ---- territory units: official bairro points are centroids only, so we
    # build real footprints by dissolving official quadras (blocks) into their
    # nearest bairro. Units without fabric (empty loteamentos) are dropped.
    raw = gpd.read_file(bairros_path).to_crs(WORKING_CRS)
    raw["nome_b"] = raw.get("nome_comp", raw.get("nome"))
    raw["bairro_id"] = [f"bairro-{i}" for i in range(len(raw))]

    if quadras_path and Path(quadras_path).exists():
        quadras = gpd.read_file(quadras_path).to_crs(WORKING_CRS)
        # official CAD data often carries self-intersections — repair first
        try:
            quadras["geometry"] = quadras.geometry.make_valid()
        except AttributeError:
            quadras["geometry"] = quadras.geometry.buffer(0)
        quadras = quadras[quadras.geometry.notna() & ~quadras.geometry.is_empty]
        pts = gpd.GeoDataFrame(
            {"bairro_id": raw["bairro_id"], "nome_b": raw["nome_b"]},
            geometry=raw.geometry,
            crs=WORKING_CRS,
        )
        joined = quadras.sjoin_nearest(pts, how="left")
        bairros = (
            joined.dissolve(by="bairro_id", as_index=False)
            .set_crs(WORKING_CRS)
        )
        names = dict(zip(pts["bairro_id"], pts["nome_b"]))
        bairros["nome_b"] = bairros["bairro_id"].map(names)
    else:
        bairros = raw

    bairros = bairros[bairros.geometry.notna() & ~bairros.geometry.is_empty]
    print(f"unidades territoriais com tecido urbano: {len(bairros)}")

    # ---- Censo 2022: population + income per bairro via sector centroids
    # (optional; first call downloads+caches the IBGE malha and agregados)
    pop_by_setor: dict[str, int | None] = {}
    renda_by_setor: dict[str, dict] = {}
    censo_releases: list[str] = []
    sectors_matched: int | None = None
    if with_censo:
        try:
            from ..sources.ibge import censo_population_by_setor, censo_renda_by_setor

            pop_by_setor, rel_pop = censo_population_by_setor()
            censo_releases.append(f"pop:{rel_pop}")
            try:
                renda_by_setor, rel_renda = censo_renda_by_setor()
                censo_releases.append(f"renda:{rel_renda}")
            except Exception as exc:  # noqa: BLE001 — renda é opcional
                print(f"renda indisponível ({exc}) — meanIncome fica null")
            bairros, sectors_matched = attach_census(bairros, pop_by_setor, renda_by_setor)
        except Exception as exc:  # noqa: BLE001 — census must never kill the analysis
            print(f"censo indisponível ({exc}) — população/renda ficam null")
    censo_release = ";".join(censo_releases) if censo_releases else "pendente"

    # attach each POI to its nearest network node, per category
    poi_nodes: dict[str, list[int]] = {c: [] for c in POI_CATEGORIES}
    xs = [g.x for g in pois.geometry]
    ys = [g.y for g in pois.geometry]
    node_ids = net.get_node_ids(xs, ys)
    for nid, cat in zip(node_ids, pois["category"]):
        if cat in poi_nodes:
            poi_nodes[cat].append(int(nid))

    for cat, nids in poi_nodes.items():
        if not nids:
            continue
        sub = pois[pois["category"] == cat]
        net.set_pois(cat, maxdist=BUDGET_M * 3, maxitems=200,
                     x_col=sub.geometry.x.values, y_col=sub.geometry.y.values)

    dists: dict[str, object] = {}
    for cat, nids in poi_nodes.items():
        if not nids:
            dists[cat] = None
            continue
        num = min(int(CAP_PER_CATEGORY), len(nids))
        dists[cat] = net.nearest_pois(BUDGET_M * 3, category=cat, num_pois=num)

    scores = []
    areas = []
    home_pts = bairros.geometry.representative_point()
    xs_b = [g.x for g in home_pts]
    ys_b = [g.y for g in home_pts]
    home_nodes = net.get_node_ids(xs_b, ys_b)


    for idx, row in enumerate(bairros.itertuples()):
        name = str(row.nome_b or "").strip()
        node = int(home_nodes[idx])

        counts: dict[str, float] = {}
        reachable: dict[str, bool] = {}
        fracs: list[float] = []
        for cat, d in dists.items():
            if d is None or node not in d.index:
                counts[cat] = 0.0
                reachable[cat] = False
                fracs.append(0.0)
                continue
            row_d = d.loc[node].dropna()
            within = int(((row_d >= 0) & (row_d <= BUDGET_M)).sum())
            counts[cat] = float(within)
            reachable[cat] = within > 0
            fracs.append(min(within / CAP_PER_CATEGORY, 1.0))

        scores.append(
            {
                "sectorId": f"bairro-{idx}",
                "bairro": name,
                "population": int(row.population) if getattr(row, "population", None) is not None else None,
                "meanIncome": _finite_or_none(
                    float(row.meanIncome) if getattr(row, "meanIncome", None) is not None else None
                ),
                "score": round(sum(fracs) / len(fracs), 3) if fracs else 0.0,
                "reachable": reachable,
                "counts": {k: int(v) for k, v in counts.items()},
            }
        )

    result = {
        "analysis": "access-score",
        "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
        "extractDates": {"osm": "overpass", "censo": censo_release},
        "timeBudgetMin": TIME_BUDGET_MIN,
        "summary": {},
        "scores": scores,
    }
    valid = [s["score"] for s in scores]
    total_pop = sum(s["population"] or 0 for s in scores)
    # city-wide income: reweight all matched sectors at once
    renda_cidade = weighted_mean(
        [
            ((renda_by_setor.get(cd) or {}).get("rendaMedia"),
             (renda_by_setor.get(cd) or {}).get("responsaveis", 0))
            for cd in pop_by_setor
        ]
    ) if renda_by_setor else None
    result["summary"] = {
        "meanScore": round(sum(valid) / len(valid), 3),
        "bestSectorId": max(scores, key=lambda s: s["score"])["sectorId"],
        "worstSectorId": min(scores, key=lambda s: s["score"])["sectorId"],
        "bairroCount": len(scores),
        "populationTotal": total_pop,
        **({"setoresCenso": sectors_matched} if sectors_matched is not None else {}),
        **({"rendaMediaCidade": renda_cidade} if renda_cidade is not None else {}),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "metrics.json", result)

    # publish the measured POIs themselves — the evidence behind the score
    import pandas as _pd  # noqa: PLC0415

    pois_wgs = pois.to_crs("EPSG:4326")
    names_col = (
        pois_wgs["name"]
        if "name" in pois_wgs.columns
        else _pd.Series([""] * len(pois_wgs), index=pois_wgs.index)
    )
    poi_features = []
    for geom, cat, nm in zip(pois_wgs.geometry, pois_wgs["category"], names_col):
        props = {"category": str(cat)}
        if isinstance(nm, str) and nm.strip() and nm.strip().lower() != "nan":
            props["name"] = nm.strip()
        poi_features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": json.loads(json.dumps(geom.__geo_interface__)),
            }
        )
    write_json(out_dir / "pois.geojson", {"type": "FeatureCollection", "features": poi_features})

    # choropleth artifact: dissolved bairro polygons + score
    def _polygonal(g):
        """Reduce to Polygon/MultiPolygon, drop slivers, simplify, round coords."""
        import shapely  # noqa: PLC0415
        from shapely.geometry import MultiPolygon as MP  # noqa: PLC0415

        if g is None or g.is_empty:
            return None
        g = shapely.make_valid(g)
        if g.geom_type not in ("Polygon", "MultiPolygon"):
            parts = []
            for sub in getattr(g, "geoms", []):
                if sub.geom_type == "Polygon":
                    parts.append(sub)
                elif sub.geom_type == "MultiPolygon":
                    parts.extend(sub.geoms)
            if not parts:
                return None
            g = MP(parts) if len(parts) > 1 else parts[0]
        if g.geom_type == "MultiPolygon":
            parts = [q for q in g.geoms if q.area >= 50]  # drop <50 m² slivers
            if not parts:
                return None
            g = MP(parts) if len(parts) > 1 else parts[0]
        g = g.simplify(2.5, preserve_topology=True)
        # gentle rounding LAST so it can't collapse geometry
        return shapely.set_precision(g, 0.05)

    features = []
    for idx, geom in enumerate(bairros.geometry):
        # clean in the projected CRS so area thresholds are in m², project after
        poly = _polygonal(geom)
        if poly is None:
            continue
        poly_wgs = (
            gpd.GeoSeries([poly], crs=WORKING_CRS).to_crs("EPSG:4326").iloc[0]
        )
        props = {
            "sectorId": scores[idx]["sectorId"],
            "name": scores[idx]["bairro"],
            "score": scores[idx]["score"],
            "counts": scores[idx]["counts"],
            "reachable": scores[idx]["reachable"],
            **(
                {"meanIncome": scores[idx]["meanIncome"]}
                if scores[idx]["meanIncome"] is not None
                else {}
            ),
        }
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": json.loads(json.dumps(poly_wgs.__geo_interface__)),
            }
        )
    write_json(out_dir / "areas.geojson", {"type": "FeatureCollection", "features": features})
    print(
        f"acesso 15min -> {len(scores)} bairros | média: {result['summary']['meanScore']} | "
        f"melhor: {result['summary']['bestSectorId']} | pior: {result['summary']['worstSectorId']}"
    )
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bairros", type=Path, required=True)
    ap.add_argument("--pois", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--quadras", type=Path, default=None)
    ap.add_argument(
        "--with-censo",
        action="store_true",
        help="join Censo 2022 population (downloads/caches IBGE malha + agregados)",
    )
    args = ap.parse_args()
    compile_access(args.bairros, args.pois, args.out, args.quadras, with_censo=args.with_censo)
