"use client";

/**
 * Ciclovias view — loads pipeline artifacts from /public/data, validates with
 * the domain schema (Zod), renders stats + map. Graceful empty state when the
 * pipeline hasn't run yet.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { z } from "zod";
import { cicloviaGapResult } from "@rio-preto/domain";
import { Stat } from "@/components/ui";

const MapClient = dynamic(() => import("@/components/ciclovias-map"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[540px] items-center justify-center rounded-xl border border-[var(--border)] text-sm text-[var(--muted)]">
      carregando mapa…
    </div>
  ),
});

const segmentsSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(z.any()),
});

type Loaded = {
  metrics: z.infer<typeof cicloviaGapResult>;
  segments: z.infer<typeof segmentsSchema>;
};

export default function CicloviasPage() {
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/data/ciclovias/metrics.json").then((r) => r.json()),
      fetch("/data/ciclovias/segments.geojson").then((r) => r.json()),
    ])
      .then(([metrics, segments]) => {
        setData({
          metrics: cicloviaGapResult.parse(metrics),
          segments: segmentsSchema.parse(segments),
        });
      })
      .catch(() =>
        setError(
          "Artefatos ainda não publicados. Rode `make snapshot && make gaps` e committe os dados.",
        ),
      );
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Ciclovias: papel × chão</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
          Compara a camada oficial de ciclovias da prefeitura com o mapeamento do
          OpenStreetMap. Rosa = existe só nos dados oficiais; âmbar = existe só no OSM;
          verde = confirmada nas duas fontes (buffer de concordância: 30 m).
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-[var(--warn)]/30 bg-amber-500/5 p-4 text-sm text-[var(--warn)]">
          {error}
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat
              label="Só no papel"
              value={`${data.metrics.summary.kmPaperOnly} km`}
              tone="danger"
              hint={`${data.metrics.summary.segmentsPaperOnly} trechos`}
            />
            <Stat
              label="Só no OSM"
              value={`${data.metrics.summary.kmOsmOnly} km`}
              tone="warn"
              hint={`${data.metrics.summary.segmentsOsmOnly} trechos`}
            />
            <Stat
              label="Confirmadas"
              value={`${data.metrics.summary.kmMatched} km`}
              tone="ok"
            />
            <Stat
              label="Extraído em"
              value={new Date(data.metrics.generatedAt).toLocaleDateString("pt-BR")}
            />
          </div>
          <MapClient segments={data.segments as unknown as GeoJSON.FeatureCollection} />
        </>
      ) : (
        <p className="text-sm text-[var(--muted)]">carregando dados…</p>
      )}
    </div>
  );
}
