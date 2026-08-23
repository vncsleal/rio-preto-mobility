"""IBGE downloads (malha + Censo 2022 setores).

Two products power the census analyses:

1. Malha de setores censitários 2022 (GeoPackage por UF) — sector polygons
   with `CD_SETOR` (15-digit geocode).
2. Agregados por Setores Censitários (CSV zips, resultados do universo) —
   population/domicile/income tables keyed by the same `CD_SETOR`.

Join rule: `CD_SETOR` starts with the 7-digit municipal geocode
(3549805 for São José do Rio Preto), so municipality filtering works even
when column names change between releases.

URLs are scraped from the directory index where filenames carry release
dates (e.g. Agregados_por_setores_basico_BR_20260520.zip), so a new IBGE
publish never breaks this module.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

import requests

from ..config import DATA_RAW, MUNICIPALITY_GEOCODE

# verified live 2026-08; the old `malhas_de_setores_censitarios__2022/`
# path returns 404 since IBGE moved the product under divisoes_intramunicipais
IBGE_MALHA_SETORES_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/gpkg/UF/SP/"
)
MALHA_SP_FILENAME = "SP_setores_CD2022.gpkg"

IBGE_AGREGADOS_URL = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/"
)
# produto separado (notas metodológicas 02/2025 e 01/2026):
# rendimento do responsável por domicílio, resultados do universo
IBGE_RENDA_URL = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Agregados_por_Setores_Censitarios_Rendimento_do_Responsavel/"
)
RENDA_ZIP_PREFIX = "Agregados_por_setores_renda_responsavel_BR"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "rio-preto-mobility/0.1 (civic research)"


def download(url: str, dest: Path) -> Path:
    """Streaming download, atomic via .part rename; skips if cached."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with SESSION.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
        tmp.rename(dest)
    return dest


def _index_files(index_url: str) -> list[str]:
    r = SESSION.get(index_url, timeout=120)
    r.raise_for_status()
    return sorted(set(re.findall(r'href="([^"]+\.(?:zip|gpkg|shp))"', r.text)))


def latest_file(index_url: str, prefix: str) -> str:
    """Newest filename in an FTP index matching a prefix (release-date names)."""
    candidates = [f for f in _index_files(index_url) if f.startswith(prefix)]
    if not candidates:
        raise RuntimeError(f"no file starting with {prefix!r} at {index_url}")
    return candidates[-1]  # sorted lexicographically == chronologically (YYYYMMDD)


def malha_sp_setores() -> Path:
    """Censo 2022 sector polygons for SP state (GeoPackage, ~100 MB)."""
    dest = raw_dir(MALHA_SP_FILENAME)
    return download(IBGE_MALHA_SETORES_URL + MALHA_SP_FILENAME, dest)


def _cached_zip(prefix: str) -> Path | None:
    """Newest already-downloaded zip matching a family prefix (offline-first)."""
    existing = sorted((DATA_RAW / "ibge").glob(f"{prefix}*.zip"))
    return existing[-1] if existing else None


def _zip_for(index_url: str, prefix: str) -> Path:
    """Cached file wins so repeated runs never depend on the flaky FTP;
    delete data/raw/ibge/<family>*.zip to force a fresh release check."""
    cached = _cached_zip(prefix)
    if cached:
        return cached
    name = latest_file(index_url, prefix)
    return download(index_url + name, raw_dir(name))


def agregados_zip(prefix: str = "Agregados_por_setores_basico_BR") -> Path:
    """Latest 'Agregados por setor' zip for a table family (basico/demografia/…)."""
    return _zip_for(IBGE_AGREGADOS_URL, prefix)


def renda_zip() -> Path:
    """Latest rendimento-do-responsável zip (dedicated IBGE product)."""
    url = IBGE_RENDA_URL + "Agregados_por_Setor_csv/"
    return _zip_for(url, RENDA_ZIP_PREFIX)


def _open_csv(zf: zipfile.ZipFile, member: str):
    """Yield DictReader rows with encoding sniffed (utf-8 first, latin-1 fallback)."""
    fh = zf.open(member)
    sample = fh.read(4096)
    fh.seek(0)
    try:
        sample.decode("utf-8-sig")
        enc = "utf-8-sig"
    except UnicodeDecodeError:
        enc = "latin-1"  # IBGE's classic encoding
    text = io.TextIOWrapper(fh, encoding=enc, errors="replace", newline="")
    return csv.DictReader(text, delimiter=";")


def _var(row: dict, code: str) -> str:
    """Variable lookup immune to case changes between IBGE releases."""
    for k, v in row.items():
        if k and k.upper() == code.upper():
            return (v or "").strip()
    return ""


def censo_setores_rows(prefix: str = "Agregados_por_setores_basico_BR") -> dict[str, dict]:
    """Rows of an agregados zip filtered to Rio Preto, keyed by CD_SETOR.

    Streams the CSV inside the zip so memory stays bounded. Municipality
    filter uses the CD_SETOR prefix — immune to column renames.
    """
    zp = agregados_zip(prefix)
    out: dict[str, dict] = {}
    with zipfile.ZipFile(zp) as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            raise RuntimeError(f"no CSV inside {zp.name}")
        for row in _open_csv(zf, csvs[0]):
            cd_setor = (row.get("CD_SETOR") or "").strip()
            if cd_setor.startswith(MUNICIPALITY_GEOCODE):
                out[cd_setor] = row
    return out


def censo_population_by_setor() -> tuple[dict[str, int | None], str]:
    """Population (v0001, universo) per CD_SETOR + release id for provenance."""
    zp = agregados_zip("Agregados_por_setores_basico_BR")
    release = zp.stem.rsplit("_", 1)[-1]  # e.g. 20260520
    pop: dict[str, int | None] = {}
    for cd, row in censo_setores_rows("Agregados_por_setores_basico_BR").items():
        raw = _var(row, "V0001")
        try:
            pop[cd] = int(raw) if raw not in ("", "X", "-", ".") else None
        except ValueError:
            pop[cd] = None
    return pop, release


def censo_renda_by_setor() -> tuple[dict[str, dict], str]:
    """Mean income of responsible persons (V06004) + weight V06001, by CD_SETOR.

    Returns ({CD_SETOR: {"rendaMedia": float|None, "responsaveis": int}}, release).
    IBGE caveat: covers only responsáveis WITH income, not all residents —
    suitable for comparison across areas, not for poverty metrics.
    """
    zp = renda_zip()
    release = zp.stem.rsplit("_", 1)[-1]
    out: dict[str, dict] = {}
    with zipfile.ZipFile(zp) as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            raise RuntimeError(f"no CSV inside {zp.name}")
        for row in _open_csv(zf, csvs[0]):
            cd = (row.get("CD_SETOR") or "").strip()
            if not cd.startswith(MUNICIPALITY_GEOCODE):
                continue
            resp_raw = _var(row, "V06001")
            inc_raw = _var(row, "V06004").replace(",", ".")
            try:
                resp = int(resp_raw) if resp_raw not in ("", ".", "X") else 0
            except ValueError:
                resp = 0
            try:
                inc: float | None = float(inc_raw) if inc_raw not in ("", ".", "X") else None
            except ValueError:
                inc = None
            out[cd] = {"rendaMedia": inc, "responsaveis": resp}
    return out, release


def raw_dir(subpath: str = "") -> Path:
    d = DATA_RAW / "ibge" / subpath
    d.parent.mkdir(parents=True, exist_ok=True)
    return d
