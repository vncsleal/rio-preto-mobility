import { existsSync } from "node:fs";
import path from "node:path";
import Link from "next/link";
import { Card, StatusBadge } from "@/components/ui";

const ANALYSES = [
  {
    href: "/ciclovias",
    title: "Ciclovias: papel × chão",
    description:
      "Cada trecho de ciclovia classificado: existe nos dados oficiais e no OSM? Só no papel? Só no OSM?",
    artifact: "ciclovias/metrics.json",
  },
  {
    href: "/quinze-minutos",
    title: "Acesso em 15 minutos",
    description:
      "Quantas escolas, postos de saúde e mercados cada bairro alcança a pé — cruzado com renda do Censo.",
    artifact: "acesso/metrics.json",
  },
  {
    href: "/transporte",
    title: "Transporte: paradas × população",
    description:
      "Que fatia da população vive a até 400 m de uma parada de ônibus — e como isso varia com a renda.",
    artifact: "transporte/metrics.json",
  },
  {
    href: "/zoneamento",
    title: "Zoneamento: o mosaico cadastral",
    description:
      "Quase 300 mil parcelas com seu código de zona — e quanto tecido formal já existe dentro de expansão e proteção.",
    artifact: "zoneamento/metrics.json",
  },
  {
    href: "/obras",
    title: "Obras: prometido × entregue",
    description:
      "Registro oficial de obras (status, prazo, custo) + fotografia semanal das camadas oficiais. Quando algo muda, fica registrado aqui.",
    artifact: "obras/projetos.json",
  },
];

const PLANNED = [
  {
    title: "GTFS: rede real",
    description:
      "Linhas, horários e velocidades do sistema RioPretrans via GTFS oficial. LAI em andamento — quando chegar, /transporte é recalculada com a rede completa.",
  },
];

function hasArtifact(rel: string): boolean {
  try {
    return existsSync(path.join(process.cwd(), "public", "data", rel));
  } catch {
    return false;
  }
}

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">
          São José do Rio Preto, em dados abertos
        </h1>
        <p className="max-w-2xl text-[var(--muted)]">
          Análises de mobilidade urbana construídas exclusivamente com fontes públicas:
          o servidor de mapas da prefeitura, OpenStreetMap e o Censo IBGE 2022. Toda
          métrica tem metodologia publicada e pipeline reproduzível.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {ANALYSES.map((a) => (
          <Link key={a.href} href={a.href} className="group">
            <Card className="h-full transition-colors group-hover:border-[var(--accent)]/50">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-medium">{a.title}</h2>
                <StatusBadge status={hasArtifact(a.artifact) ? "live" : "aguardando-dados"} />
              </div>
              <p className="mt-2 text-sm text-[var(--muted)]">{a.description}</p>
            </Card>
          </Link>
        ))}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          No radar
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {PLANNED.map((a) => (
            <Card key={a.title} className="opacity-75">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium">{a.title}</h3>
                <StatusBadge status="planejado" />
              </div>
              <p className="mt-2 text-sm text-[var(--muted)]">{a.description}</p>
            </Card>
          ))}
        </div>
      </section>

      <section>
        <Card>
          <h2 className="font-medium">Como ler este site</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            <li>Nenhuma opinião sem evidência: cada número linka para o método.</li>
            <li>Dados oficiais podem estar errados — quando estiverem, isso também é um achado.</li>
            <li>Tudo é refazível: clone o repositório e rode o pipeline você mesmo.</li>
          </ul>
        </Card>
      </section>
    </div>
  );
}
