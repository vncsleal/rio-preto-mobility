import { Card } from "@/components/ui";

const SOURCES = [
  {
    name: "Prefeitura de São José do Rio Preto",
    detail:
      "Servidor ArcGIS público (sig.riopreto.sp.gov.br). Camadas: ciclovias, corredores, zoneamento, plano diretor. Snapshot semanal com checksum.",
  },
  {
    name: "OpenStreetMap",
    detail:
      "Overpass API, município = relation 298344. Infraestrutura cicloviária: highway=cycleway, cycleway=*, path com bicycle=designated.",
  },
  {
    name: "IBGE Censo 2022",
    detail:
      "Setores censitários (malha oficial) + população e rendimento por setor.",
  },
];

export default function MetodologiaPage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Metodologia</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
          Transparência total: se um número aqui está errado, qualquer pessoa pode
          descobrir por quê.
        </p>
      </header>

      <div className="space-y-3">
        {SOURCES.map((s) => (
          <Card key={s.name}>
            <h2 className="font-medium">{s.name}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">{s.detail}</p>
          </Card>
        ))}
      </div>

      <Card>
        <h2 className="font-medium">Como o gap de ciclovias é calculado</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-[var(--muted)]">
          <li>Baixamos a camada oficial de ciclovias (EPSG:4326) e reprojetamos para UTM 22S (EPSG:31982) — todas as distâncias em metro.</li>
          <li>Fazemos o mesmo com a infraestrutura cicloviária mapeada no OpenStreetMap.</li>
          <li>Cada trecho oficial que não intersecta nenhum trecho OSM em 30 metros é classificado como &ldquo;só no papel&rdquo; — e vice-versa.</li>
          <li>Comprimentos são somados por categoria; o resultado vai para /data/ciclovias/metrics.json.</li>
        </ol>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Limitações conhecidas: OSM pode estar incompleto (um trecho &ldquo;só no
          papel&rdquo; pode existir fisicamente); a camada oficial pode usar geometrias
          simplificadas. Sempre citamos a data do extract.
        </p>
      </Card>
    </div>
  );
}
