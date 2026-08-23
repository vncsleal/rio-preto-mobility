# Rio Preto em Dados

Mobilidade urbana de São José do Rio Preto-SP com fontes 100% abertas e pipeline
reproduzível. Domínio TypeScript (Zod) + app Next.js + compilador Python.

## Quickstart

```sh
pnpm install
make setup          # venv Python + deps geo+network
make snapshot       # baixa camadas oficiais (ArcGIS público)
make gaps           # compila análise de ciclovias -> apps/web/public/data/
pnpm dev            # http://localhost:3000
```

## Layout

```
packages/domain   schemas Zod — contratos de todos os artifacts
pipeline/         compilador Python: sources -> compile -> publish
apps/web/         Next.js 16, MapLibre + deck.gl, consome artifacts estáticos
launchd/          job semanal de snapshot (zero GitHub Actions)
scripts/          commit do snapshot semanal
```

## Fontes

**Prefeitura (ArcGIS público)** — snapshot semanal com checksum (`sources/targets.py`):
ciclovias, corredores/miniterminais, plano diretor (macrozoneamento, perímetro,
plano viário), avenida de contorno, ferrovia, bairros, **obras cadastradas**
(status/prazo/custo/construtora), unidades de saúde, equipamentos sociais e
setores censitários com geocódigo IBGE. Pesadas sob demanda
(`make snapshot-heavy`): zoneamento parcelar, logradouros, quadras fiscais.

**OpenStreetMap** — Overpass API: infraestrutura cicloviária e POIs de
educação/saúde/comércio para o score de 15 minutos.

**IBGE Censo 2022** — malha de setores + agregados por setor
(população/domicílios/rendimento), filtrados por prefixo de geocódigo
(3549805). Ver `sources/ibge.py`; junção com setores da prefeitura via `CD_SETOR`.

## Comandos

| Target | O que faz |
|---|---|
| `make setup` | venv + deps `[geo,network]` |
| `make snapshot` | fotografia das camadas leves |
| `make snapshot-heavy` | inclui zoneamento/logradouros/quadras |
| `make snapshot --only <slug…>` | camadas específicas |
| `make gaps` | análise ciclovias papel × chão |
| `make acesso` | score 15 min por bairro (requer rede OSM em cache) |
| `make obras && make projetos` | diffs entre snapshots + registro oficial de obras |
| `make test` | testes unitários dos helpers puros |

Tiles PMTiles (opcional, p/ camadas pesadas): `brew install tippecanoe pmtiles`
— sem os binários o pipeline serve GeoJSON normalmente.

## Princípio

Dados brutos são o domínio; tudo no site é artifact gerado. O frontend nunca fala
com a prefeitura em runtime. Ver `PLAN.md` para o plano completo.

> O modelo de accountability assume histórico git (o launchd semanal faz
> fetch→diff→commit→push). Clone precisa de `git init` + remote antes do
> primeiro `make snapshot-commit`.
