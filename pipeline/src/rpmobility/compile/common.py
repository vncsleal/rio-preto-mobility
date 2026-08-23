"""Shared building blocks for the bairro-level compilers.

Territory units and census sectors are identical across analyses, so both
access_score (15-min) and stop_coverage (/transporte) consume them from here.
"""

from __future__ import annotations

from pathlib import Path

from ..config import WORKING_CRS


def build_territory_units(bairros_path: Path, quadras_path: Path | None = None):
    """Official bairro footprints in WORKING_CRS.

    The city's ArcGIS layer only publishes centroid points per bairro, so we
    build real polygons by dissolving official quadras (blocks) into their
    nearest bairro point. Units without urban fabric are dropped. Returns a
    GeoDataFrame with columns bairro_id / nome_b.
    """
    import geopandas as gpd

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
        units = joined.dissolve(by="bairro_id", as_index=False).set_crs(WORKING_CRS)
        names = dict(zip(pts["bairro_id"], pts["nome_b"]))
        units["nome_b"] = units["bairro_id"].map(names)
    else:
        units = raw

    units = units[units.geometry.notna() & ~units.geometry.is_empty]
    print(f"unidades territoriais com tecido urbano: {len(units)}")
    return units


def municipal_setores(units):
    """Censo 2022 sector polygons for the municipality, in WORKING_CRS."""
    import geopandas as gpd

    from ..config import MUNICIPALITY_GEOCODE
    from ..sources.ibge import malha_sp_setores

    gpkg = malha_sp_setores()
    # bbox must be in the file's CRS (4326): transform bounds before reading
    bounds_wgs = tuple(units.to_crs("EPSG:4326").total_bounds)
    setores = gpd.read_file(gpkg, bbox=bounds_wgs)
    setores = setores[setores["CD_MUN"].astype(str) == MUNICIPALITY_GEOCODE].to_crs(WORKING_CRS)
    return setores[setores.geometry.notna() & ~setores.geometry.is_empty]


def polygonal(g):
    """Reduce to Polygon/MultiPolygon, drop slivers, simplify, round coords."""
    import shapely
    from shapely.geometry import MultiPolygon as MP

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
