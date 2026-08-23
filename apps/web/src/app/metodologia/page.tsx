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
        <h2 className="font-medium">Como o mosaico de zoneamento é calculado</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-[var(--muted)]">
          <li>Baixamos a base cadastral da prefeitura: ~292 mil parcelas com código de zona (ZONA/ZONEAMENTO) e área territorial declarada.</li>
          <li>A prefeitura publica essas parcelas <em>sem geometria</em> — então vinculamos cada parcela ao bairro oficial pelo nome normalizado (acentos, abreviações como JD/PQ e ordem de palavras tratadas; ~84% de aderência).</li>
          <li>Cada bairro oficial (polígono real, dissolução das quadras) recebe sua macrozona pelo centróide.</li>
          <li>&ldquo;Pressão urbana&rdquo; = parcelas em bairros cuja macrozona é EXPANSÃO, PROTEÇÃO ou RESTRIÇÃO — tecido formal dentro de zona não consolidada.</li>
        </ol>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Limitações conhecidas: a atribuição é por bairro, não por parcela;
          nomes novos de loteamentos ficam sem vínculo (16%); o centróide pode
          cair na macrozona vizinha em bairros limítrofes.
        </p>
      </Card>

      <Card>
        <h2 className="font-medium">Como a cobertura de paradas é calculada</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-[var(--muted)]">
          <li>Baixamos as paradas de ônibus mapeadas no OpenStreetMap (highway=bus_stop e public_transport=platform com bus=yes).</li>
          <li>Cada setor censitário do Censo 2022 é representado pelo seu ponto central; a população do setor vem dos agregados oficiais.</li>
          <li>Um setor é &ldquo;coberto&rdquo; se seu ponto central cai num raio de 400 m em linha reta de qualquer parada.</li>
          <li>Por bairro: soma da população coberta ÷ população total. A leitura de equidade compara bairros em tercis de renda do responsável.</li>
        </ol>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Limitações conhecidas: o OSM pode ter paradas faltando (o GTFS oficial
          substituirá esta fonte); raio em linha reta superestima caminhadas
          reais; o centróide do setor é uma aproximação da distribuição interna
          da população.
        </p>
      </Card>

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
