"""Unit tests for pure pipeline helpers — no network, no geo deps."""

from __future__ import annotations

import datetime as dt

from rpmobility.compile.obras_projetos import normalize_project, summarize
from rpmobility.config import geojson_checksum
from rpmobility.snapshot import diff_summary
from rpmobility.sources.arcgis import _esri_geometry_to_geojson


class TestChecksum:
    def test_stable_across_key_order(self):
        a = {"type": "FeatureCollection", "features": [{"a": 1}]}
        b = {"features": [{"a": 1}], "type": "FeatureCollection"}
        assert geojson_checksum(a) == geojson_checksum(b)

    def test_changes_with_content(self):
        a = {"type": "FeatureCollection", "features": []}
        b = {"type": "FeatureCollection", "features": [{"id": 1}]}
        assert geojson_checksum(a) != geojson_checksum(b)


class TestDiffSummary:
    def test_first_snapshot(self):
        d = diff_summary(None, {"features": []}, None, "abc")
        assert d == {"changed": True, "reason": "first snapshot", "checksum": "abc"}

    def test_unchanged(self):
        fc = {"features": [{"properties": {"x": 1}}]}
        d = diff_summary(fc, {"features": [{"properties": {"x": 1}}]}, "k", "k")
        assert d["changed"] is False

    def test_added_removed(self):
        old = {"features": [{"properties": {"x": 1}}, {"properties": {"x": 2}}]}
        new = {"features": [{"properties": {"x": 2}}, {"properties": {"x": 3}}]}
        d = diff_summary(old, new, "a", "b")
        assert d["changed"] is True
        assert d["added"] == 1
        assert d["removed"] == 1


class TestEsriGeometry:
    def test_point(self):
        g = _esri_geometry_to_geojson({"x": -49.3, "y": -20.8})
        assert g == {"type": "Point", "coordinates": [-49.3, -20.8]}

    def test_polygon_ring_closing(self):
        rings = [[[0, 0], [1, 0], [1, 1], [0, 0]]]
        g = _esri_geometry_to_geojson({"rings": rings})
        assert g["type"] == "Polygon"
        assert g["coordinates"][0][0] == g["coordinates"][0][-1]

    def test_single_path_linestring(self):
        g = _esri_geometry_to_geojson({"paths": [[[0, 0], [1, 1]]]})
        assert g["type"] == "LineString"

    def test_multi_path(self):
        g = _esri_geometry_to_geojson({"paths": [[[0, 0]], [[1, 1]]]})
        assert g["type"] == "MultiLineString"

    def test_null(self):
        assert _esri_geometry_to_geojson({}) is None
        assert _esri_geometry_to_geojson(None) is None


class TestCensoAggregation:
    def test_weighted_mean(self):
        from rpmobility.compile.access_score import weighted_mean

        assert weighted_mean([(6503.65, 175), (2000.0, 25)]) == 5940.69
        assert weighted_mean([(None, 10), (100.0, 5)]) == 100.0
        assert weighted_mean([(100.0, 0)]) is None
        assert weighted_mean([]) is None

    def test_population_sums_into_bairros(self):
        import geopandas as gpd
        from shapely.geometry import Point, Polygon

        from rpmobility.compile.access_score import attach_census

        # two "bairros" as squares; one sector centroid inside each,
        # one rural sector outside both
        sq_a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        sq_b = Polygon([(20, 0), (30, 0), (30, 10), (20, 10)])
        bairros = gpd.GeoDataFrame(
            {"bairro_id": ["bairro-0", "bairro-1"]},
            geometry=[sq_a, sq_b],
            crs="EPSG:31982",
        )
        setores = gpd.GeoDataFrame(
            {
                "CD_SETOR": ["3549805000001", "3549805000002", "3549805001003"],
                "pop": [120, 80, 999],  # rural one must be ignored
            },
            geometry=[Point(5, 5), Point(25, 5), Point(50, 50)],
            crs="EPSG:31982",
        )

        # monkeypatch the malha download/read by injecting via sjoin path —
        # instead call the internal join directly on prepared frames
        pts = setores.copy()
        pts["geometry"] = pts.geometry.representative_point()
        joined = gpd.sjoin(
            pts[["CD_SETOR", "pop", "geometry"]],
            bairros[["bairro_id", "geometry"]],
            how="inner",
            predicate="within",
        )
        sums = joined.groupby("bairro_id")["pop"].sum()
        out = bairros.copy()
        out["population"] = out["bairro_id"].map(sums).fillna(0).astype(int)

        assert list(out["population"]) == [120, 80]
        assert len(joined.drop_duplicates("CD_SETOR")) == 2


class TestStopCoverage:
    def test_coverage_share(self):
        from rpmobility.compile.stop_coverage import coverage_share

        assert coverage_share(0, 0) == 0.0
        assert coverage_share(100, 50) == 0.5
        assert coverage_share(100, 200) == 1.0  # clamped
        assert coverage_share(3, 1) == 0.3333

    def test_tercile_means(self):
        from rpmobility.compile.stop_coverage import tercile_means

        # renda ascending, coverage rising with income -> clean gradient
        pairs = [(float(i), i / 9) for i in range(9)]
        t = tercile_means(pairs)
        assert set(t) == {"baixa", "media", "alta"}
        assert t["baixa"] < t["media"] < t["alta"]
        assert t["baixa"] == 0.111 and t["media"] == 0.444 and t["alta"] == 0.778

    def test_tercile_skips_missing_income(self):
        from rpmobility.compile.stop_coverage import tercile_means

        pairs = [(None, 0.9), (100.0, 0.1), (200.0, 0.2), (300.0, 0.3)]
        t = tercile_means(pairs)
        assert t == {"baixa": 0.1, "media": 0.2, "alta": 0.3}

    def test_tercile_too_few(self):
        from rpmobility.compile.stop_coverage import tercile_means

        assert tercile_means([(100.0, 0.1), (200.0, 0.2)]) == {}


class TestObrasProjetos:
    def test_normalize_full(self):
        p = normalize_project(
            {
                "globalid": "abc",
                "finalidade": "TOP/0026/21 - Reforma",
                "status": "andamento",
                "inic_obra": 1637290800000,
                "term_obra": 1677466800000,
                "custo_obra": 398297.812,
                "orig_recurso": "Recurso Próprio",
                "emp_construtora": "Pradela",
                "secretaria_fiscal": "SEMOB",
            },
            (-49.3, -20.8),
        )
        assert p["status"] == "andamento"
        assert p["statusLabel"] == "em andamento"
        assert p["inicio"].startswith("2021-11-19")
        assert p["custo"] == 398297.81
        assert p["lon"] == -49.3

    def test_normalize_missing_fields(self):
        p = normalize_project({}, None)
        assert p["status"] == "desconhecido"
        assert p["inicio"] is None
        assert p["custo"] is None
        assert p["lat"] is None

    def test_summarize_overdue(self):
        past = (dt.datetime.now(dt.UTC) - dt.timedelta(days=10)).isoformat()
        future = (dt.datetime.now(dt.UTC) + dt.timedelta(days=30)).isoformat()
        projetos = [
            {"id": "1", "status": "andamento", "terminoPrevisto": past, "custo": 100.0},
            {"id": "2", "status": "a_iniciar", "terminoPrevisto": future, "custo": None},
            {"id": "3", "status": "concluido", "terminoPrevisto": past, "custo": 50.0},
        ]
        s = summarize(projetos, dt.datetime.now(dt.UTC))
        assert s["total"] == 3
        assert s["porStatus"] == {"andamento": 1, "a_iniciar": 1, "concluido": 1}
        assert s["atrasadas"] == 1  # concluded-but-late doesn't count
        assert s["custoPorStatus"]["andamento"] == 100.0
