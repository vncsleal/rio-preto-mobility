"""Catalog of ArcGIS layers tracked by the snapshot job.

Service paths may omit /MapServer. Layer ids must be LEAF layers —
querying a group layer returns HTTP 400 ("Invalid or missing input
parameters"), so groups were expanded manually via the REST catalog.

Heavy layers (tens of thousands of features or very slow server-side
queries) are excluded from the weekly job and fetched on demand with
`make snapshot-heavy`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackedLayer:
    service: str
    layer_id: int
    slug: str
    description: str


TRACKED_LAYERS: tuple[TrackedLayer, ...] = (
    TrackedLayer("Planejamento/CICLOVIAS", 0, "ciclovias", "Ciclovias oficiais"),
    TrackedLayer("Obras/Corredores_Miniterminais", 1, "corredores_onibus", "Corredores de ônibus"),
    TrackedLayer("Obras/Corredores_Miniterminais", 2, "miniterminais", "Miniterminais"),
    TrackedLayer("Obras/Plano_Diretor", 1, "macrozoneamento", "Macrozoneamento"),
    TrackedLayer("Obras/Plano_Diretor", 2, "perimetro_urbano", "Perímetro urbano"),
    TrackedLayer("Obras/Plano_Diretor", 3, "plano_viario", "Plano viário"),
    TrackedLayer("Planejamento/Avenida_de_Contorno", 0, "contorno", "Projeto Avenida de Contorno"),
    TrackedLayer("Planejamento/Ferrovia", 0, "ferrovia", "Ferrovia"),
    TrackedLayer("Hosted/Bairros/FeatureServer", 0, "bairros", "Bairros oficiais (agregação)"),
    # obras cadastradas: pontos com status/prazo/custo/construtora — a matéria-
    # prima real do "prometido × entregue" (184 registros em 2026-08)
    TrackedLayer(
        "Hosted/Obras_MapLayer/FeatureServer",
        0,
        "obras_pontos",
        "Obras cadastradas (status, prazos, custo)",
    ),
    # unidades oficiais de saúde — POI autoritativo p/ análise de acesso
    TrackedLayer("Hosted/Saude/FeatureServer", 0, "saude_unidades", "Unidades de saúde"),
    TrackedLayer(
        "Hosted/Equipamentos_Desenvolvimento_Social/FeatureServer",
        0,
        "equip_social",
        "Equipamentos de desenvolvimento social",
    ),
    # setores censitários com geocódigo de 15 dígitos — chave de junção
    # com os agregados do Censo 2022 (CD_SETOR)
    TrackedLayer(
        "Hosted/Setores_Censitarios/FeatureServer",
        0,
        "setores_censitarios",
        "Setores censitários (geocódigo IBGE)",
    ),
)

# Slow/huge: fetched only on demand (count query alone can exceed 60s).
HEAVY_LAYERS: tuple[TrackedLayer, ...] = (
    TrackedLayer("Obras/ZONEAMENTO", 0, "zoneamento", "Zoneamento oficial (parcelas)"),
    TrackedLayer("Logradouros_Atual", 0, "logradouros", "Rede viária oficial (~25k trechos)"),
    TrackedLayer(
        "Hosted/Quadras/FeatureServer",
        1,
        "quadras",
        "Quadras fiscais (~15k polígonos, ~95 MB) — base das unidades territoriais",
    ),
)
