"""Shared config and paths for the rpmobility pipeline."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("RIO_MOBILITY_ROOT", Path(__file__).resolve().parents[3])
)
DATA_RAW = REPO_ROOT / "data" / "raw"
SNAPSHOTS = DATA_RAW / "snapshots"
LATEST = SNAPSHOTS / "latest"
WEB_PUBLIC_DATA = REPO_ROOT / "apps" / "web" / "public" / "data"

# City ArcGIS Server (verified live)
ARCGIS_BASE = "https://sig.riopreto.sp.gov.br/server/rest/services"

# Municipal boundary: OpenStreetMap relation 298344
OSM_RELATION_ID = 298344

# All distance math happens here; artifacts are published in EPSG:4326.
WORKING_CRS = "EPSG:31982"  # SIRGAS 2000 / UTM 22S


@dataclass(frozen=True)
class Paths:
    raw: Path = DATA_RAW
    snapshots: Path = SNAPSHOTS
    latest: Path = LATEST
    web_data: Path = WEB_PUBLIC_DATA


def geojson_checksum(geojson: dict) -> str:
    """Stable sha256 of a GeoJSON dict — cheap diff detection between snapshots."""
    payload = json.dumps(geojson, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
