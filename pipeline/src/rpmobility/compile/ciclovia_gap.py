"""Analysis 1 — ciclovia gap: official city layer vs OSM cycle infrastructure.

Pure compiler: paths in -> artifacts out. Requires the [geo] extra
(geopandas/shapely) for the spatial match.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from ..config import WORKING_CRS, write_json

MATCH_BUFFER_M = 30.0


def _require_geo():
    try:
        import geopandas as gpd  # noqa: F401
        from shapely.geometry import Point  # noqa: F401

        return gpd
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "missing geo deps — run: uv pip install -e 'pipeline[geo]'"
        ) from exc


def compile_gap(city_path: Path, osm_path: Path, out_dir: Path) -> dict:
    gpd = _require_geo()

    # prefer the snapshot's real extract date over the "latest" pointer name
    city_extract = city_path.parent.name
    meta = city_path.parent / f"{city_path.stem}.meta.json"
    if meta.exists():
        import json as _json

        fetched = _json.loads(meta.read_text()).get("fetchedAt")
        if fetched:
            city_extract = fetched[:10]

    city = gpd.read_file(city_path).to_crs(WORKING_CRS)
    osm = gpd.read_file(osm_path).to_crs(WORKING_CRS)

    for gdf, prefix in ((city, "city"), (osm, "osm")):
        if gdf.empty:
            raise SystemExit(f"{prefix} input has no features: {gdf} {city_path}")
        gdf["length_m"] = gdf.geometry.length

    osm_buf = osm.buffer(MATCH_BUFFER_M).union_all()
    city_buf = city.buffer(MATCH_BUFFER_M).union_all()

    def classify(gdf, other_buf, kind_when_missed, source):
        hit = gdf.intersects(other_buf)
        out = gdf.copy()
        out["kind"] = [kind_when_missed if not h else "matched" for h in hit]
        out["source"] = source
        return out

    from shapely.ops import unary_union  # noqa: F401

    city_c = classify(city, osm_buf, "paper-only", "city")
    osm_c = classify(osm, city_buf, "osm-only", "osm")

    def clean_name(row) -> str:
        import math

        for key in ("name", "nome", "NOME"):
            val = row.get(key)
            if val is None:
                continue
            if isinstance(val, float) and math.isnan(val):
                continue
            s = str(val).strip()
            if s and s.lower() != "nan":
                return s
        return ""

    segments = []
    for gdf in (city_c, osm_c):
        gdf_wgs84 = gdf.to_crs("EPSG:4326")
        for i, row in gdf_wgs84.iterrows():
            segments.append(
                {
                    "type": "Feature",
                    "properties": {
                        "id": f"{row['source']}-{i}",
                        "kind": row["kind"],
                        "name": clean_name(row),
                        "lengthM": round(float(row["length_m"]), 1),
                        "source": row["source"],
                    },
                    "geometry": json.loads(json.dumps(row.geometry.__geo_interface__)),
                }
            )

    km = lambda kind, src: round(  # noqa: E731
        sum(s["properties"]["lengthM"] for s in segments
            if s["properties"]["kind"] == kind and s["properties"]["source"] == src) / 1000,
        2,
    )
    result = {
        "analysis": "ciclovia-gap",
        "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
        "extractDates": {"city": city_extract, "osm": "overpass"},
        "matchBufferM": MATCH_BUFFER_M,
        "summary": {
            "kmPaperOnly": km("paper-only", "city"),
            "kmOsmOnly": km("osm-only", "osm"),
            "kmMatched": km("matched", "city"),
            "segmentsPaperOnly": sum(1 for s in segments if s["properties"]["kind"] == "paper-only"),
            "segmentsOsmOnly": sum(1 for s in segments if s["properties"]["kind"] == "osm-only"),
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "segments.geojson", {"type": "FeatureCollection", "features": segments})
    write_json(out_dir / "metrics.json", result)
    print(
        f"ciclovia gap -> papel: {result['summary']['kmPaperOnly']} km | "
        f"só-OSM: {result['summary']['kmOsmOnly']} km | "
        f"confirmadas: {result['summary']['kmMatched']} km"
    )
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--city", type=Path, required=True)
    ap.add_argument("--osm", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    compile_gap(args.city, args.osm, args.out)
