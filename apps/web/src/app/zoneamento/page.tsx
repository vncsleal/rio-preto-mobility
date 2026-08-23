"use client";

/**
 * Zoneamento view — the cadastral mosaic: ~292k parcels by zoning code,
 * attached to official bairros, with the macrozone pressure read.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { z } from "zod";
import { zoneamentoResult } from "@rio-preto/domain";
import { Card, Stat } from "@/components/ui";

const ZoneamentoMap = dynamic(() => import("@/components/zoneamento-map"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[540px] items-center justify-center rounded-xl border border-[var(--border)] text-sm text-[var(--muted)]">
      carregando mapa…
    </div>
  ),
});

const fcSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(z.any()),
});

type Loaded = {
  metrics: z.infer<typeof zoneamentoResult>;
  areas: z.infer<typeof fcSchema>;
  macros: z.infer<typeof fcSchema>;
  hasQuadrasTiles: boolean;
};

const fmt = (n: number) => n.toLocaleString("pt-BR");

export default function ZoneamentoPage() {
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showQuadras, setShowQuadras] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch("/data/zoneamento/metrics.json").then((r) => r.json()),
      fetch("/data/zoneamento/areas.geojson").then((r) => r.json()),
      fetch("/data/zoneamento/macros.geojson").then((r) => r.json()),
      fetch("/data/tiles/manifest.json")
        .then((r) => (r.ok ? r.json() : { tiles: {} }))
        .catch(() => ({ tiles: {} })),
    ])
      .then(([metrics, areas, macros, manifest]) =>
        setData({
          metrics: zoneamentoResult.parse(metrics),
          areas: fcSchema.parse(areas),
          macros: fcSchema.parse(macros),
          hasQuadrasTiles: Boolean(manifest.tiles?.quadras),
        }),
      )
      .catch(() =>
        setError(
          "Artefatos ainda não publicados. Rode `make snapshot-heavy && make zoneamento`.",
        ),
      );
  }, []);

  if (error) {
    return (
      <div className="space-y-6">
        <Header />
        <div className="rounded-xl border border-[var(--warn)]/30 bg-amber-500/5 p-4 text-sm text-[var(--warn)]">
          {error}
        </div>
      </div>
    );
  }

  if (!data) return <p className="text-sm text-[var(--muted)]">carregando dados…</p>;

  const { metrics } = data;
  const s = metrics.summary;
  const pressao = s.parcelasMacrozonaNaoUrbana ?? 0;
  const pressaoPct = s.parcelas ? (pressao / s.parcelas) * 100 : 0;

  return (
    <div className="space-y-6">
      <Header />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat
          label="Parcelas cadastradas"
          value={fmt(s.parcelas)}
          hint={`${fmt(s.categoriasZona)} categorias de zona`}
        />
        <Stat
          label="Área cadastrada"
          value={`${(s.areaTotalHa / 100).toFixed(0)} km²`}
          hint={`${fmt(s.parcelasSemZona)} parcelas sem zona`}
        />
        <Stat
          label="Em macrozona não-urbana"
          value={`${pressaoPct.toFixed(0)}%`}
          tone={pressaoPct > 20 ? "warn" : "default"}
          hint={`${fmt(pressao)} parcelas · ${s.haMacrozonaNaoUrbana?.toLocaleString("pt-BR")} ha`}
        />
        <Stat
          label="Bairros vinculados"
          value={`${Math.round((s.bairroMatch.matched / (s.bairroMatch.matched + s.bairroMatch.unmatched)) * 100)}%`}
          hint={`${fmt(s.bairroMatch.unmatched)} parcelas sem bairro oficial`}
        />
      </div>

      {data.hasQuadrasTiles && (
        <div className="flex items-center gap-2 text-sm">
          <button
            type="button"
            onClick={() => setShowQuadras((v) => !v)}
            className={`rounded-md border px-3 py-1.5 transition-colors ${
              showQuadras
                ? "border-[var(--accent)]/50 bg-[var(--accent)]/10 text-[var(--text)]"
                : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            Malha urbana (quadras fiscais)
          </button>
          <span className="text-xs text-[var(--muted)]">
            via PMTiles — 15 mil quadras em um arquivo de 9 MB
          </span>
        </div>
      )}

      <ZoneamentoMap
        areas={data.areas as unknown as GeoJSON.FeatureCollection}
        macros={data.macros as unknown as GeoJSON.FeatureCollection}
        showQuadras={showQuadras && data.hasQuadrasTiles}
      />

      <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--muted)]">
        <span className="font-medium text-[var(--text)]">Parcelas por bairro:</span>
        <span className="flex items-center gap-1.5">
          <span className="size-3 rounded" style={{ background: "#fdf4e3" }} /> poucas
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-3 rounded" style={{ background: "#e05a3c" }} /> muitas
        </span>
        <span className="ml-2 font-medium text-[var(--text)]">Contornos:</span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4" style={{ background: "#fb923c" }} /> Expansão
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4" style={{ background: "#34d399" }} /> Proteção
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4" style={{ background: "#60a5fa" }} /> Consolidada
        </span>
      </div>

      <Card>
        <h2 className="mb-3 font-medium">Pressão urbana por macrozona</h2>
        <p className="mb-3 text-xs text-[var(--muted)]">
          Parcelas cadastradas cujo bairro cai dentro de cada macrozona do plano
          diretor — o tecido formal que já existe fora do consolidado.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="pb-2 pr-4">Macrozona</th>
                <th className="pb-2 pr-4">Bairros</th>
                <th className="pb-2 pr-4">Parcelas</th>
                <th className="pb-2 pr-4">Área parcelada</th>
                <th className="pb-2">Zona da cidade</th>
              </tr>
            </thead>
            <tbody>
              {metrics.macrozonas.map((mz) => (
                <tr key={mz.name} className="border-b border-[var(--border)]/50">
                  <td className="py-2.5 pr-4 font-medium">{mz.name}</td>
                  <td className="py-2.5 pr-4 tabular-nums">{mz.bairros}</td>
                  <td className="py-2.5 pr-4 tabular-nums">{fmt(mz.parcelas)}</td>
                  <td className="py-2.5 pr-4 tabular-nums">{fmt(mz.areaParcelasHa)} ha</td>
                  <td className={`py-2.5 ${mz.naoUrbana ? "text-[var(--warn)]" : "text-[var(--ok)]"}`}>
                    {mz.naoUrbana ? "não urbana" : "urbana"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-medium">Categorias de zoneamento</h2>
        <p className="mb-3 text-xs text-[var(--muted)]">
          Os códigos numéricos são os da própria base da prefeitura; a legenda
          oficial por código está no plano diretor. Área = soma das áreas
          territoriais declaradas por parcela.
        </p>
        <div className="space-y-1.5">
          {metrics.porZona.slice(0, 10).map((zt) => {
            const max = metrics.porZona[0].parcelas || 1;
            return (
              <div key={zt.zona} className="flex items-center gap-3 text-sm">
                <span className="w-12 shrink-0 tabular-nums text-[var(--muted)]">{zt.zona}</span>
                <div className="h-2 flex-1 overflow-hidden rounded bg-white/5">
                  <div
                    className="h-full rounded bg-[var(--accent)]"
                    style={{ width: `${(zt.parcelas / max) * 100}%` }}
                  />
                </div>
                <span className="w-24 shrink-0 text-right tabular-nums">{fmt(zt.parcelas)}</span>
                <span className="w-28 shrink-0 text-right tabular-nums text-[var(--muted)]">
                  {fmt(Math.round(zt.areaHa))} ha
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <p className="text-sm text-[var(--muted)]">
          <strong className="text-[var(--text)]">Nota metodológica:</strong> a
          prefeitura publica as ~292 mil parcelas <em>sem geometria</em> (apenas
          atributos), então a ligação com o mapa é pelo nome do bairro no
          cadastro casado com a camada oficial ({s.bairroMatch.matched.toLocaleString("pt-BR")}{" "}
          parcelas vinculadas; as demais são loteamentos novos ausentes da
          camada oficial — em si um achado). A atribuição de macrozona usa o
          centróide do bairro. Extraído do snapshot{" "}
          {metrics.extractDate}. Veja a{" "}
          <a href="/metodologia" className="underline hover:text-[var(--text)]">
            metodologia
          </a>
          .
        </p>
      </Card>
    </div>
  );
}

function Header() {
  return (
    <header>
      <h1 className="text-2xl font-semibold tracking-tight">Zoneamento: o mosaico cadastral</h1>
      <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
        Como o solo da cidade está dividido na prática: quase 300 mil parcelas
        com seu código de zona, cruzadas com as macrozonas do plano diretor.
        Onde já existe cidade formalizada dentro de zonas de expansão e proteção?
      </p>
    </header>
  );
}
