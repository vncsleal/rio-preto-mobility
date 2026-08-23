"""
Analysis 5 — zoneamento: o mosaico cadastral em parcelas.

The city's cadastre carries ~292k parcels, each tagged with a zoning code
(ZONA/ZONEAMENTO), a use level (NIVEL) and territorial area (AREATER).
Caveat discovered the hard way: BOTH ArcGIS views of this table
(Obras/ZONEAMENTO and Obras/NIVEIS_USO) serve attributes only — parcel
geometry is withheld. So:

- the mosaic is aggregated from pure attributes;
- parcels attach to official bairros by normalized name matching (~84%);
- each official bairro (real polygons from dissolved quadras) gets its
  macrozone attributed via centroid — the urban-pressure read: how much
  cadastral fabric already sits inside EXPANSÃO/PROTEÇÃO/RESTRIÇÃO.

Raw parcels are never published — aggregates only.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
from pathlib import Path

from ..config import LATEST, WEB_PUBLIC_DATA, WORKING_CRS, write_json
from .common import build_territory_units, polygonal

# norm_txt() strips accents, so compare against unaccented forms
NON_URBAN_MACROS = {"EXPANSAO", "PROTECAO", "RESTRICAO"}

# cadastre BAIRRO strings vs official layer names diverge on abbreviations
# (JD/JARDIM), accents (JOAO/JOÃO), filler words and word order.
_EXPANSIONS = {"JD": "JARDIM", "PQ": "PARQUE", "RES": "RESIDENCIAL",
               "VL": "VILA", "CH": "CHACARA", "STO": "SANTO", "STA": "SANTA"}
_TYPE_WORDS = {"JARDIM", "PARQUE", "RESIDENCIAL", "VILA", "LOTEAMENTO",
               "CONDOMINIO", "CONJUNTO", "HABITACIONAL", "FAZENDA", "ESTANCIA", "CHACARA"}
_STOP = {"DA", "DO", "DE", "DAS", "DOS"}


def norm_txt(s) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def canon_bairro(s) -> frozenset[str]:
    """Distinctive-token signature of a bairro name (order/type-word blind)."""
    toks = (_EXPANSIONS.get(t, t) for t in norm_txt(s).split())
    return frozenset(t for t in toks if t not in _STOP and t not in _TYPE_WORDS)


class BairroNameIndex:
    """Exact-signature lookup with unique-superset fallback (~84% hit rate)."""

    def __init__(self):
        self._exact: dict[frozenset[str], str] = {}
        self._by_token: dict[str, set[frozenset[str]]] = collections.defaultdict(set)

    def add(self, bairro_id: str, name: str) -> None:
        sig = canon_bairro(name)
        if not sig:
            return
        self._exact.setdefault(sig, bairro_id)
        for t in sig:
            self._by_token[t].add(sig)

    def resolve(self, name: str) -> str | None:
        sig = canon_bairro(name)
        if not sig:
            return None
        hit = self._exact.get(sig)
        if hit:
            return hit
        # subset fallback only: parcel name must be strictly less specific
        # than exactly one official name ("Solidariedade" ⊂ "Solidariedade I").
        # Equal-size near-matches ("... II" vs "... I") stay unmatched.
        cands: set[frozenset[str]] | None = None
        for t in sig:
            s = self._by_token.get(t, set())
            cands = s if cands is None else cands & s
            if not cands:
                return None
        supersets = [c for c in (cands or ()) if sig < c]
        return next(iter(self._exact[c] for c in supersets)) if len(supersets) == 1 else None


def attr(props: dict, short: str):
    """ArcGIS keeps dotted field names ('SJRP.Parcelas.ZONA') in GeoJSON
    exports; match by case-insensitive suffix."""
    want = short.upper()
    for k, v in props.items():
        if k.upper().split(".")[-1] == want:
            return v
    return None


def safe_float(v) -> float:
    """float() that maps junk ('nan', '', None, 'X') to 0.0 — NaN must never
    reach strict-JSON artifacts."""
    import math

    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if math.isfinite(f) else 0.0


def macro_index(macros_gdf):
    """(lookup(point) -> NAME, names) built once for all bairro centroids."""
    import numpy as np
    from shapely.strtree import STRtree

    names = [norm_txt(v) for v in macros_gdf["NAME"]]
    tree = STRtree(list(macros_gdf.geometry))

    def lookup(point):
        hits = tree.query(np.asarray([point]), predicate="intersects")
        return names[int(hits[1][0])] if len(hits[1]) else None

    return lookup


def compile_zoneamento(
    parcels_path: Path,
    out_dir: Path,
    quadras_path: Path | None = None,
    bairros_path: Path | None = None,
) -> dict:
    import geopandas as gpd
    from shapely.strtree import STRtree

    units = build_territory_units(
        bairros_path or (LATEST / "bairros.geojson"),
        quadras_path or (LATEST / "quadras.geojson"),
    )
    name_index = BairroNameIndex()
    for urow in units.itertuples():
        name_index.add(urow.bairro_id, str(urow.nome_b or ""))

    # ---- single pass over the parcels (attributes only: the server
    # withholds parcel geometry on both views of this table)
    print(f"lendo {parcels_path.name} …")
    fc = json.loads(Path(parcels_path).read_text())

    por_zona: collections.Counter = collections.Counter()
    area_zona: collections.Counter = collections.Counter()
    bc: collections.Counter = collections.Counter()
    ba: collections.Counter = collections.Counter()
    bz: collections.defaultdict = collections.defaultdict(collections.Counter)
    divergentes = sem_zona = matched = unmatched = 0

    for f in fc["features"]:
        p = f.get("properties", {})
        zona_raw = norm_txt(attr(p, "ZONA"))
        zona = norm_txt(attr(p, "ZONEAMENTO")) or zona_raw
        if not zona or zona in ("NONE", "."):
            sem_zona += 1
            zona_out = ""
        else:
            por_zona[zona] += 1
            area_zona[zona] += safe_float(attr(p, "AREATER"))
            if zona_raw and zona != zona_raw:
                divergentes += 1
            zona_out = zona

        key = name_index.resolve(attr(p, "BAIRRO"))
        if key is None:
            unmatched += 1
        else:
            matched += 1
            a = safe_float(attr(p, "AREATER"))
            bc[key] += 1
            ba[key] += a
            bz[key][zona_out or "?"] += 1
    del fc
    total = sum(por_zona.values())
    print(
        f"parcelas com zona: {total} | sem zona: {sem_zona} | "
        f"ZONA≠ZONEAMENTO: {divergentes} | bairro casado: {matched}/{matched+unmatched}"
    )

    result: dict = {
        "analysis": "zoneamento-mosaico",
        "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
        "extractDate": Path(parcels_path).resolve().parent.name,
        "summary": {
            "parcelas": total,
            "parcelasSemZona": sem_zona,
            "zonaDivergente": divergentes,
            "categoriasZona": len(por_zona),
            "areaTotalHa": round(sum(area_zona.values()) / 10_000, 1),
            "bairroMatch": {"matched": matched, "unmatched": unmatched},
        },
        "porZona": [
            {"zona": z, "parcelas": n, "areaHa": round(area_zona[z] / 10_000, 1)}
            for z, n in por_zona.most_common()
        ],
    }

    # ---- macrozone attribution: bairro centroid -> macrozone NAME.
    # Pressure read = cadastral fabric already inside non-urban macrozones.
    macros_path = LATEST / "macrozoneamento.geojson"
    macro_stats: dict[str, dict] = {}
    macro_of_bairro: dict[str, str] = {}
    if macros_path.exists():
        import numpy as np

        macros = gpd.read_file(macros_path).to_crs(WORKING_CRS)
        names = [norm_txt(v) for v in macros["NAME"]]
        tree = STRtree(list(macros.geometry))
        centroids = units.geometry.representative_point()
        left, right = tree.query(
            np.asarray(gpd.GeoSeries(centroids, crs=WORKING_CRS).array),
            predicate="intersects",
        )
        for li, ri in zip(left, right):
            macro_of_bairro[units.iloc[int(li)]["bairro_id"]] = names[int(ri)]
        for i, row in macros.iterrows():
            name = names[int(i)]
            entry = macro_stats.setdefault(
                name,
                {
                    "name": name,
                    "poligonos": 0,
                    "areaKm2": 0.0,
                    "populacaoDeclarada": None,
                    "bairros": sum(1 for m in macro_of_bairro.values() if m == name),
                    "parcelas": sum(int(bc[b]) for b, m in macro_of_bairro.items() if m == name),
                    "areaParcelasHa": round(
                        sum(float(ba[b]) for b, m in macro_of_bairro.items() if m == name)
                        / 10_000,
                        1,
                    ),
                    "naoUrbana": name in NON_URBAN_MACROS,
                },
            )
            entry["poligonos"] += 1
            try:
                entry["areaKm2"] += safe_float(row.get("AREA_KM2"))
            except (TypeError, ValueError):
                pass
            if entry["populacaoDeclarada"] is None:
                try:
                    entry["populacaoDeclarada"] = int(float(row.get("POPULACAO")))
                except (TypeError, ValueError):
                    pass
        for e in macro_stats.values():
            e["areaKm2"] = round(e["areaKm2"], 1)
        result["macrozonas"] = sorted(macro_stats.values(), key=lambda m: -m["parcelas"])
        result["summary"]["parcelasMacrozonaNaoUrbana"] = sum(
            m["parcelas"] for m in macro_stats.values() if m["naoUrbana"]
        )
        result["summary"]["haMacrozonaNaoUrbana"] = round(
            sum(m["areaParcelasHa"] for m in macro_stats.values() if m["naoUrbana"]), 1
        )

    # ---- choropleth artifact (bairro polygons + dominant zoning)
    areas = []
    for urow in units.itertuples():
        bid = urow.bairro_id
        poly = polygonal(urow.geometry)
        if poly is None:
            continue
        top = bz[bid].most_common(3)
        props = {
            "sectorId": bid,
            "name": str(urow.nome_b or ""),
            "parcels": int(bc.get(bid, 0)),
            "areaHa": round(ba.get(bid, 0.0) / 10_000, 1),
            "dominantZone": top[0][0] if top else None,
            "topZonas": {z: int(n) for z, n in top},
            "macrozona": macro_of_bairro.get(bid),
        }
        poly_wgs = gpd.GeoSeries([poly], crs=WORKING_CRS).to_crs("EPSG:4326").iloc[0]
        areas.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": json.loads(json.dumps(poly_wgs.__geo_interface__)),
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "areas.geojson", {"type": "FeatureCollection", "features": areas})
    write_json(out_dir / "metrics.json", result)

    # simplified macrozone overlay
    if macros_path.exists():
        macros_g = gpd.read_file(macros_path).to_crs(WORKING_CRS)
        names_g = [norm_txt(v) for v in macros_g["NAME"]]
        macros_wgs = gpd.GeoSeries(macros_g.geometry, crs=WORKING_CRS).to_crs("EPSG:4326")
        feats = []
        for i, poly in enumerate(macros_wgs):
            clean = polygonal(poly)
            if clean is None:
                continue
            stats = macro_stats.get(names_g[i], {})
            feats.append(
                {
                    "type": "Feature",
                    "properties": {
                        "name": names_g[i].title(),
                        "naoUrbana": bool(stats.get("naoUrbana")),
                        "parcelas": int(stats.get("parcelas", 0)),
                        "areaParcelasHa": stats.get("areaParcelasHa", 0),
                    },
                    "geometry": json.loads(json.dumps(clean.__geo_interface__)),
                }
            )
        write_json(out_dir / "macros.geojson", {"type": "FeatureCollection", "features": feats})

    s = result["summary"]
    print(
        f"zoneamento -> {s['parcelas']} parcelas | {s['categoriasZona']} zonas | "
        f"{s['areaTotalHa']} ha | pressão não-urbana: "
        f"{s.get('parcelasMacrozonaNaoUrbana', 0)} parcelas ({s.get('haMacrozonaNaoUrbana', 0)} ha)"
    )
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parcels", type=Path, default=LATEST / "zoneamento.geojson")
    ap.add_argument("--bairros", type=Path, default=LATEST / "bairros.geojson")
    ap.add_argument("--quadras", type=Path, default=LATEST / "quadras.geojson")
    ap.add_argument("--out", type=Path, default=WEB_PUBLIC_DATA / "zoneamento")
    args = ap.parse_args()
    compile_zoneamento(args.parcels, args.out, args.quadras, args.bairros)
