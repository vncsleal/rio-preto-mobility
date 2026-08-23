"use client";

/**
 * 15-minutos view — bairro-level walk accessibility to educação/saúde/comércio.
 * Validates artifacts with the domain schema before rendering.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { z } from "zod";
import { accessScoreResult } from "@rio-preto/domain";
import { Card, Stat } from "@/components/ui";

const AcessoMap = dynamic(() => import("@/components/acesso-map"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[540px] items-center justify-center rounded-xl border border-[var(--border)] text-sm text-[var(--muted)]">
      carregando mapa…
    </div>
  ),
});

const areasSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(z.any()),
});

const CATEGORY_LABELS: Record<string, string> = {
  educacao: "educação",
  saude: "saúde",
  comercio: "comércio",
};

type Loaded = {
  metrics: z.infer<typeof accessScoreResult>;
  areas: z.infer<typeof areasSchema>;
  pois: z.infer<typeof areasSchema>;
};

export default function QuinzeMinutosPage() {
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/data/acesso/metrics.json").then((r) => r.json()),
      fetch("/data/acesso/areas.geojson").then((r) => r.json()),
      fetch("/data/acesso/pois.geojson").then((r) => r.json()),
    ])
      .then(([metrics, areas, pois]) => {
        setData({
          metrics: accessScoreResult.parse(metrics),
          areas: areasSchema.parse(areas),
          pois: areasSchema.parse(pois),
        });
      })
      .catch(() =>
        setError(
          "Artefatos ainda não publicados. Rode `make acesso` e committe os dados.",
        ),
      );
  }, []);

  const nameOf = (id: string | null) =>
    id ? data?.metrics.scores.find((s) => s.sectorId === id)?.bairro ?? id : "—";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Acesso em 15 minutos</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
          A partir do centro de cada bairro: quantos equipamentos de educação,
          saúde e comércio são alcançáveis a pé (raio de ~1,1 km pela rede de
          calçadas/vias do OSM). Score = fração das categorias bem atendidas,
          saturando em 5 equipamentos por categoria.
        </p>
        <p className="mt-2 max-w-2xl text-xs text-[var(--muted)]">
          Nota metodológica: os limites dos bairros são aproximados — dissolução
          das quadras oficiais (14.674) atribuídas ao bairro mais próximo; a
          prefeitura publica apenas pontos-centróide por bairro.
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
              label="Score médio"
              value={`${(data.metrics.summary.meanScore * 100).toFixed(0)}%`}
            />
            <Stat label="Melhor bairro" value={nameOf(data.metrics.summary.bestSectorId)} tone="ok" />
            <Stat label="Pior bairro" value={nameOf(data.metrics.summary.worstSectorId)} tone="danger" />
            {data.metrics.summary.populationTotal ? (
              <Stat
                label="População avaliada"
                value={data.metrics.summary.populationTotal.toLocaleString("pt-BR")}
                hint={`Censo 2022 · ${data.metrics.summary.bairroCount} bairros`}
              />
            ) : (
              <Stat label="Bairros avaliados" value={String(data.metrics.summary.bairroCount)} />
            )}
          </div>

          <AcessoMap areas={data.areas as unknown as GeoJSON.FeatureCollection} pois={data.pois as unknown as GeoJSON.FeatureCollection} />

          <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--muted)]">
            <span className="font-medium text-[var(--text)]">Bairro (score):</span>
            <span className="flex items-center gap-1.5">
              <span className="size-3 rounded" style={{ background: "#64748b" }} /> nada a pé
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-3 rounded" style={{ background: "#fb7185" }} /> fraco
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-3 rounded" style={{ background: "#fbbf24" }} /> razoável
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-3 rounded" style={{ background: "#34d399" }} /> completo
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--muted)]">
            <span className="font-medium text-[var(--text)]">Pontos medidos:</span>
            <span className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ background: "#38bdf8" }} /> educação
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ background: "#e879f9" }} /> saúde
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ background: "#facc15" }} /> comércio
            </span>
          </div>

          <Card>
            <p className="text-sm text-[var(--muted)]">
              <strong className="text-[var(--text)]">Fontes:</strong> população por
              bairro = soma dos setores censitários do Censo IBGE 2022 cujo
              centróide cai no bairro (release{" "}
              {data.metrics.extractDates.censo}). Renda média por setor entra
              quando o IBGE publica os arquivos finais de rendimento. Categorias:{" "}
              {Object.values(CATEGORY_LABELS).join(", ")}.
            </p>
          </Card>
        </>
      ) : (
        <p className="text-sm text-[var(--muted)]">carregando dados…</p>
      )}
    </div>
  );
}
