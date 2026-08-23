"""Analysis 3b — obras cadastradas: the city's own construction registry.

The ArcGIS layer Hosted/Obras_MapLayer carries one point per obra with
status (a_iniciar | andamento | concluido), start/finish dates, cost,
funding source and contractor. This is accountability data proper:
"prometido × entregue" per project, not per layer diff.

Pure normalization lives in normalize_project/summarize so it is unit-
testable without network or filesystem.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from ..config import LATEST, WEB_PUBLIC_DATA, write_json

_STATUS_LABELS = {
    "a_iniciar": "a iniciar",
    "andamento": "em andamento",
    "concluido": "concluída",
}


def _epoch_ms_to_iso(v) -> str | None:
    if v in (None, "", 0):
        return None
    try:
        return dt.datetime.fromtimestamp(int(v) / 1000, dt.UTC).isoformat()
    except (TypeError, ValueError):
        return None


def normalize_project(attrs: dict, coords: tuple[float, float] | None) -> dict:
    """Raw ArcGIS attributes -> domain-shaped project dict."""
    status = str(attrs.get("status") or "desconhecido").strip().lower()
    custo = attrs.get("custo_obra")
    proj = {
        "id": str(attrs.get("globalid") or attrs.get("objectid") or ""),
        "finalidade": str(attrs.get("finalidade") or "").strip(),
        "status": status,
        "statusLabel": _STATUS_LABELS.get(status, status),
        "inicio": _epoch_ms_to_iso(attrs.get("inic_obra")),
        "terminoPrevisto": _epoch_ms_to_iso(attrs.get("term_obra")),
        "custo": round(float(custo), 2) if isinstance(custo, (int, float)) else None,
        "origemRecurso": str(attrs.get("orig_recurso") or "").strip() or None,
        "construtora": str(attrs.get("emp_construtora") or "").strip() or None,
        "secretaria": str(attrs.get("secretaria_fiscal") or "").strip() or None,
        "lon": coords[0] if coords else None,
        "lat": coords[1] if coords else None,
    }
    return proj


def summarize(projetos: list[dict], now: dt.datetime) -> dict:
    """Aggregate counts/costs + overdue detection from normalized projects."""
    by_status: dict[str, int] = {}
    custo_by_status: dict[str, float] = {}
    atrasadas = []
    for p in projetos:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
        if p["custo"] is not None:
            custo_by_status[p["status"]] = (
                custo_by_status.get(p["status"], 0.0) + p["custo"]
            )
        # prevista para terminar antes de hoje e ainda não concluída
        if p["status"] != "concluido" and p["terminoPrevisto"]:
            fim = dt.datetime.fromisoformat(p["terminoPrevisto"])
            if fim < now:
                atrasadas.append(p["id"])
    return {
        "total": len(projetos),
        "porStatus": by_status,
        "custoPorStatus": {k: round(v, 2) for k, v in custo_by_status.items()},
        "atrasadas": len(atrasadas),
    }


def compile_projects(obras_path: Path, out_dir: Path) -> dict:
    import json

    fc = json.loads(obras_path.read_text())
    projetos = []
    for f in fc["features"]:
        geom = f.get("geometry") or {}
        coords = (
            tuple(geom["coordinates"]) if geom.get("type") == "Point" else None
        )
        projetos.append(normalize_project(f.get("properties", {}), coords))

    now = dt.datetime.now(dt.UTC)
    result = {
        "analysis": "obras-projetos",
        "generatedAt": now.isoformat(),
        "extractDate": obras_path.parent.name,
        "summary": summarize(projetos, now),
        "projetos": sorted(
            projetos,
            key=lambda p: (p["status"] != "andamento", p["status"] != "a_iniciar", p["finalidade"]),
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "projetos.json", result)
    s = result["summary"]
    print(
        f"obras projetos -> {s['total']} obras | andamento: "
        f"{s['porStatus'].get('andamento', 0)} | atrasadas: {s['atrasadas']}"
    )
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--obras", type=Path, default=LATEST / "obras_pontos.geojson")
    ap.add_argument("--out", type=Path, default=WEB_PUBLIC_DATA / "obras")
    args = ap.parse_args()
    compile_projects(args.obras, args.out)
