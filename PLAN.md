# Rio Preto Mobility — plano técnico (stack TS)

Pipeline que cruza **dados oficiais da prefeitura (ArcGIS REST)**, **OpenStreetMap** e **Censo IBGE 2022** em dashboards interativos para os debates de urbanismo de São José do Rio Preto-SP.

Princípio herdado do ARCHITECTURE.md: **dados brutos são o domínio; tudo no site é artifact gerado, nunca autorado.** O frontend nunca fala com a prefeitura em runtime — só consome arquivos pré-gerados e hospedados estaticamente.

---

## Stack

| Camada | Escolha | Por quê |
|---|---|---|
| App | Next.js 16 (App Router) + React 19 | seu daily driver |
| UI | Tailwind v4 + shadcn/ui + lucide | idem |
| Gráficos | shadcn/charts (Recharts) | já é seu padrão |
| Mapa base | **MapLibre GL JS** via `react-map-gl/maplibre` | open-source, sem API key |
| Camadas pesadas | **deck.gl v9** (`@deck.gl/mapbox` `MapboxOverlay`, modo overlaid) | GPU, mantém controls/popups do MapLibre |
| Tiles | **PMTiles** single-file (tippecanoe) + basemap Protomaps | serve de qualquer host estático, custo zero |
| ETL | Python mínimo (geopandas/osmnx) rodando como *compiler* | rede/pandana não existe em JS; TS domina a apresentação |
| Contratos | Zod schemas em `packages/domain`; metrics.json validado | domínio único, consumers derivados |
| CI | **zero-minutes**: launchd semanal no Mac (fetch→diff→commit→push), pipeline roda local, lefthook pre-push | Actions minutos são escassos (ver openplan); runner self-hosted é inseguro p/ repo público |
| Deploy | Cloudflare Pages com build próprio da CF | não consome Actions; PMTiles funciona via range requests |

## Estrutura

```
rio-preto-mobility/
├── apps/web/                      # Next.js 16
│   └── app/
│       ├── page.tsx               # overview com números-chave
│       ├── ciclovias/             # análise 1
│       ├── quinze-minutos/        # análise 2
│       ├── obras/                 # análise 3 (timeline prometido vs entregue)
│       ├── transporte/            # análise 4 (cobertura paradas × renda)
│       ├── zoneamento/            # análise 5
│       └── metodologia/           # uma página por análise, linguagem simples
├── packages/domain/
│   └── src/                       # Zod schemas: Layer, Metric, AnalysisResult, SnapshotDiff
├── pipeline/
│   ├── sources/
│   │   ├── arcgis.py              # fetch paginado, cache data/raw/
│   │   ├── osm.py                 # osmnx graphs + overpass
│   │   └── ibge.py                # setores censitários 2022
│   ├── compile/                   # domain → artifacts (funções puras, sem I/O)
│   │   ├── ciclovia_gap.py
│   │   ├── access_score.py
│   │   ├── stop_coverage.py
│   │   └── plano_vs_realidade.py
│   └── publish/                   # tippecanoe → .pmtiles + metrics.json
└── public/data/                   # artifacts versionados servidos pelo Next
    ├── tiles/*.pmtiles
    └── metrics/*.json
```

## Fases

1. **Semana 1 — esqueleto + ingestão**
   - [ ] Repo pnpm/turbo, Next.js 16, Tailwind v4, shadcn init
   - [ ] `packages/domain`: schemas Zod (LayerSnapshot, GapSegment, AccessScore, StopCoverage)
   - [ ] `pipeline/sources/*` com cache idempotente em `data/raw/`
2. **Semana 2 — primeira análise ponta a ponta**
   - [ ] `compile/ciclovia_gap.py` (match buffer 30 m cidade vs OSM)
   - [ ] `publish/`: GeoJSON → tippecanoe → `ciclovias.pmtiles`
   - [ ] Rota `/ciclovias`: react-map-gl + deck.gl PathLayer + painel lateral shadcn
3. **Semanas 3–4 — acessibilidade**
   - [ ] pandana isócronas × Censo 2022 × renda
   - [ ] `/quinze-minutos`: choropleth HexagonLayer/PolygonLayer + seletor de POIs
4. **Mês 2 — accountability**
   - [ ] launchd plist semanal → snapshot camadas ArcGIS → diff automático → commit+push
   - [ ] `/obras`: timeline "prometido vs entregue" alimentada por diffs
   - [ ] LAI enviada pedindo GTFS + bilhetagem (lead time)
5. **Depois**
   - [ ] `/transporte` (paradas × renda), `/zoneamento` (conflitos), r5r pós-GTFS

## Decisões travadas

- **CRS**: EPSG:31982 (SIRGAS 2000 UTM 22S) p/ todo cálculo; 4326 só nos artifacts finais (web)
- **ArcGIS**: paginar sempre (`resultOffset` ≤ maxRecordCount ~1000–2000)
- **Basemap**: Protomaps PMTiles próprio (sem depender de provedor externo/keyless)
- **CI mínimo**: snapshots e builds do pipeline são batch — rodam localmente e commitam artifacts; nada automático por push. Único workflow opcional: `workflow_dispatch` de emergência
- **Repo público** (transparência é o produto) ⇒ nunca usar runner self-hosted aqui (forks podem rodar código arbitrário — ver runbook openplan)
- **Metodologia pública**: toda página de análise linka método + data do extract + repositório
