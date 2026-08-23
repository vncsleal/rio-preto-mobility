"use client";

/**
 * Transporte view — pre-GTFS stop coverage: share of each bairro's population
 * (Censo 2022) within 400 m of an OSM-mapped bus stop, read against income.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { z } from "zod";
import { stopCoverageResult } from "@rio-preto/domain";
import { Card, Stat } from "@/components/ui";

const TransporteMap = dynamic(() => import("@/components/transporte-map"), {
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
  metrics: z.infer<typeof stopCoverageResult>;
  areas: z.infer<typeof fcSchema>;
  stops: z.infer<typeof fcSchema>;
};

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export default function TransportePage() {
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/data/transporte/metrics.json").then((r) => r.json()),
      fetch("/data/transporte/areas.geojson").then((r) => r.json()),
      fetch("/data/transporte/stops.geojson").then((r) => r.json()),
    ])
      .then(([metrics, areas, stops]) =>
        setData({
          metrics: stopCoverageResult.parse(metrics),
          areas: fcSchema.parse(areas),
          stops: fcSchema.parse(stops),
        }),
      )
      .catch(() =>
        setError(
          "Artefatos ainda não publicados. Rode `make transporte` e committe os dados.",
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
  const tercis = metrics.summary.porTercilRenda;
  const piores = [...metrics.coberturas]
    .filter((c) => c.population > 0)
    .sort((a, b) => a.coverageShare - b.coverageShare)
    .slice(0, 10);

  return (
    <div className="space-y-6">
      <Header />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Paradas mapeadas" value={String(metrics.summary.stopsTotal)} hint="OpenStreetMap — pré-GTFS" />
        <Stat
          label="População a ≤400 m"
          value={`${(metrics.summary.coberturaMedia * 100).toFixed(0)}%`}
          tone={metrics.summary.coberturaMedia > 0.5 ? "ok" : "warn"}
          hint={`${metrics.summary.popCoberta.toLocaleString("pt-BR")} de ${metrics.summary.popTotal.toLocaleString("pt-BR")} hab.`}
        />
        {tercis && (
          <Stat
            label="Cobertura tercil de renda alta"
            value={`${(tercis.alta * 100).toFixed(0)}%`}
            tone="ok"
            hint={`baixa: ${(tercis.baixa * 100).toFixed(0)}% · média: ${(tercis.media * 100).toFixed(0)}%`}
          />
        )}
        <Stat label="Bairros avaliados" value={String(metrics.coberturas.length)} />
      </div>

      <TransporteMap areas={data.areas as unknown as GeoJSON.FeatureCollection} stops={data.stops as unknown as GeoJSON.FeatureCollection} />

      <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--muted)]">
        <span className="font-medium text-[var(--text)]">Cobertura da população:</span>
        <span className="flex items-center gap-1.5">
          <span className="size-3 rounded" style={{ background: "#64748b" }} /> nenhuma
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-3 rounded" style={{ background: "#fbbf24" }} /> baixa
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-3 rounded" style={{ background: "#34d399" }} /> alta
        </span>
        <span className="ml-2 flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ background: "#3b82f6" }} /> parada OSM
        </span>
      </div>

      {tercis && (
        <Card>
          <h2 className="font-medium">Paradas × renda</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Bairros em tercis de renda média do responsável (Censo 2022). A
            diferença entre os extremos é o achado de equidade desta análise:
            cobertura de{" "}
            <strong className="text-[var(--ok)]">{(tercis.baixa * 100).toFixed(0)}%</strong> nos
            bairros mais pobres contra{" "}
            <strong className="text-[var(--accent)]">{(tercis.alta * 100).toFixed(0)}%</strong> nos
            mais ricos.
          </p>
          <div className="mt-3 flex h-3 overflow-hidden rounded-full">
            <div className="bg-[var(--danger)]" style={{ width: `${tercis.baixa * 100}%` }} />
            <div className="flex-1 bg-[var(--warn)]" />
            <div className="bg-[var(--ok)]" style={{ width: `${tercis.alta * 100}%` }} />
          </div>
          <div className="mt-1 flex justify-between text-xs text-[var(--muted)]">
            <span>tercil baixa renda</span>
            <span>média</span>
            <span>alta renda</span>
          </div>
        </Card>
      )}

      <Card>
        <h2 className="mb-3 font-medium">Dez bairros menos cobertos (com população)</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                <th className="pb-2 pr-4">Bairro</th>
                <th className="pb-2 pr-4">População</th>
                <th className="pb-2 pr-4">% a ≤400 m</th>
                <th className="pb-2">Renda média</th>
              </tr>
            </thead>
            <tbody>
              {piores.map((c) => (
                <tr key={c.sectorId} className="border-b border-[var(--border)]/50">
                  <td className="py-2.5 pr-4 font-medium">{c.bairro || c.sectorId}</td>
                  <td className="py-2.5 pr-4 tabular-nums">{c.population.toLocaleString("pt-BR")}</td>
                  <td className="py-2.5 pr-4 tabular-nums text-[var(--danger)]">
                    {(c.coverageShare * 100).toFixed(0)}%
                  </td>
                  <td className="py-2.5 tabular-nums">
                    {c.meanIncome != null ? brl(c.meanIncome) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <p className="text-sm text-[var(--muted)]">
          <strong className="text-[var(--text)]">Nota metodológica:</strong>{" "}
          {metrics.source === "gtfs" ? (
            <>
              paradas do <strong className="text-[var(--text)]">GTFS oficial</strong> (
              {metrics.extractDates.osm}) — a rede completa do sistema
              RioPretrans, com todas as paradas servidas por linhas regulares.
            </>
          ) : (
            <>
              paradas vêm do OpenStreetMap — o mapeamento pode estar incompleto e
              enviesado para áreas centrais; os números mudarão quando o GTFS oficial
              for liberado (LAI em andamento, ver{" "}
              <code>docs/lai-gtfs.md</code> no repositório).
            </>
          )}{" "}
          Cobertura medida em linha reta do centróide do setor censitário à
          parada, raio de {metrics.radiusM.toFixed(0)} m ({metrics.extractDates.censo}).
          Veja a{" "}
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
      <h1 className="text-2xl font-semibold tracking-tight">Transporte: paradas × população</h1>
      <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
        Quantos moradores de cada bairro vivem a até 400 m de uma parada de ônibus
        mapeada no OpenStreetMap — cruzado com a renda do Censo 2022. Versão
        preliminar enquanto o GTFS oficial não é liberado.
      </p>
    </header>
  );
}
