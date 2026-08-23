"use client";

/**
 * Obras view — inventory of tracked official layers + diff timeline.
 * Validates artifacts with the domain schema before rendering.
 */

import { useEffect, useState } from "react";
import { z } from "zod";
import { obrasProjectsResult, obrasTimelineResult } from "@rio-preto/domain";
import { Card, Stat } from "@/components/ui";

type Loaded = z.infer<typeof obrasTimelineResult>;
type Projetos = z.infer<typeof obrasProjectsResult>;

const STATUS_TONE: Record<string, string> = {
  andamento: "text-[var(--accent)]",
  a_iniciar: "text-[var(--warn)]",
  concluido: "text-[var(--ok)]",
};

const brl = (v: number) =>
  v >= 1e6
    ? `R$ ${(v / 1e6).toFixed(1)} mi`
    : `R$ ${(v / 1e3).toFixed(0)} mil`;

const fmtDate = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
};

export default function ObrasPage() {
  const [data, setData] = useState<Loaded | null>(null);
  const [projetos, setProjetos] = useState<Projetos | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/data/obras/metrics.json")
      .then((r) => r.json())
      .then((m) => setData(obrasTimelineResult.parse(m)))
      .catch(() =>
        setError(
          "Artefatos ainda não publicados. Rode `make snapshot && make obras` e committe os dados.",
        ),
      );
    // registro oficial de obras — falha é tolerável, a timeline segue útil
    fetch("/data/obras/projetos.json")
      .then((r) => r.json())
      .then((p) => setProjetos(obrasProjectsResult.parse(p)))
      .catch(() => {});
  }, []);

  const lastChecked = data?.layers.reduce<string | null>(
    (max, l) => (max && max > l.lastChecked ? max : l.lastChecked),
    null,
  );

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Obras: prometido × entregue</h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
          Toda semana fotografamos as camadas oficiais (corredores de ônibus,
          avenida de contorno, plano diretor). Mudanças ficam registradas aqui com
          data — o histórico do git é a linha do tempo.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-[var(--warn)]/30 bg-amber-500/5 p-4 text-sm text-[var(--warn)]">
          {error}
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Camadas monitoradas" value={String(data.layers.length)} />
            <Stat label="Fotografias" value={String(data.snapshotsAnalyzed)} />
            <Stat label="Mudanças detectadas" value={String(data.events.length)} tone={data.events.length > 0 ? "warn" : "default"} />
            <Stat label="Última verificação" value={lastChecked ? fmtDate(lastChecked) : "—"} />
          </div>

          {projetos && (
            <>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat
                  label="Obras no registro oficial"
                  value={String(projetos.summary.total)}
                  hint="camada Obras_MapLayer da prefeitura"
                />
                <Stat
                  label="Em andamento"
                  value={String(projetos.summary.porStatus.andamento ?? 0)}
                  tone="default"
                />
                <Stat
                  label="Prazo vencido"
                  value={String(projetos.summary.atrasadas)}
                  tone={projetos.summary.atrasadas > 0 ? "danger" : "ok"}
                  hint="término previsto antes de hoje, não concluídas"
                />
                <Stat
                  label={`Custo (em andamento)`}
                  value={brl(projetos.summary.custoPorStatus.andamento ?? 0)}
                />
              </div>

              <Card>
                <h2 className="mb-3 font-medium">Registro de obras</h2>
                <p className="mb-3 text-xs text-[var(--muted)]">
                  Cada linha é uma obra cadastrada pela prefeitura, com status,
                  prazo e custo declarados. Ordenado: em andamento → a iniciar →
                  concluídas.
                </p>
                <div className="max-h-[420px] overflow-y-auto">
                  <table className="w-full min-w-[640px] text-sm">
                    <thead className="sticky top-0 bg-[var(--panel)]">
                      <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                        <th className="pb-2 pr-4">Obra</th>
                        <th className="pb-2 pr-4">Status</th>
                        <th className="pb-2 pr-4">Término previsto</th>
                        <th className="pb-2">Custo</th>
                      </tr>
                    </thead>
                    <tbody>
                      {projetos.projetos.map((p) => {
                        const atrasada =
                          p.status !== "concluido" &&
                          p.terminoPrevisto !== null &&
                          new Date(p.terminoPrevisto) < new Date();
                        return (
                          <tr key={p.id} className="border-b border-[var(--border)]/50 align-top">
                            <td className="py-2.5 pr-4">
                              {p.finalidade || "sem descrição"}
                              {p.construtora && (
                                <span className="block text-xs text-[var(--muted)]">
                                  {p.construtora}
                                  {p.origemRecurso ? ` · ${p.origemRecurso}` : ""}
                                </span>
                              )}
                            </td>
                            <td className={`py-2.5 pr-4 whitespace-nowrap ${STATUS_TONE[p.status] ?? ""}`}>
                              {p.statusLabel}
                              {atrasada && (
                                <span className="ml-1 rounded bg-red-500/10 px-1.5 py-0.5 text-xs text-[var(--danger)]">
                                  atrasada
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 pr-4 tabular-nums whitespace-nowrap">
                              {p.terminoPrevisto ? fmtDate(p.terminoPrevisto) : "—"}
                            </td>
                            <td className="py-2.5 tabular-nums whitespace-nowrap">
                              {p.custo !== null ? brl(p.custo) : "—"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          )}

          <Card>
            <h2 className="mb-3 font-medium">Inventário atual</h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
                    <th className="pb-2 pr-4">Camada</th>
                    <th className="pb-2 pr-4">Feições</th>
                    <th className="pb-2 pr-4">Estável desde</th>
                    <th className="pb-2">Verificado em</th>
                  </tr>
                </thead>
                <tbody>
                  {data.layers.map((l) => (
                    <tr key={l.slug} className="border-b border-[var(--border)]/50">
                      <td className="py-2.5 pr-4">
                        <span className="font-medium">{l.slug}</span>
                        {l.description && (
                          <span className="block text-xs text-[var(--muted)]">{l.description}</span>
                        )}
                      </td>
                      <td className="py-2.5 pr-4 tabular-nums">{l.featureCount}</td>
                      <td className="py-2.5 pr-4 tabular-nums">{fmtDate(l.stableSince)}</td>
                      <td className="py-2.5 tabular-nums">{fmtDate(l.lastChecked)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 font-medium">Linha do tempo</h2>
            {data.events.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                Primeira fotografia tirada — nenhuma mudança registrada ainda. A
                partir da próxima rodada semanal, qualquer alteração nas camadas
                oficiais aparece aqui com data e contagem de feições.
              </p>
            ) : (
              <ol className="space-y-3">
                {[...data.events].reverse().map((e, i) => (
                  <li key={`${e.slug}-${e.to}-${i}`} className="flex gap-3 text-sm">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-[var(--warn)]" />
                    <span>
                      <strong>{e.slug}</strong> mudou entre{" "}
                      {fmtDate(e.from)} → {fmtDate(e.to)}{" "}
                      <span className="text-[var(--muted)]">
                        (+{e.added} / −{e.removed} feições)
                      </span>
                    </span>
                  </li>
                ))}
              </ol>
            )}
            <p className="mt-4 border-t border-[var(--border)] pt-3 text-xs text-[var(--muted)]">
              Contabilizamos feições adicionadas e removidas por comparação de
              atributos; edições puramente geométricas (sem criar/apagar feição)
              podem não aparecer na contagem — o checksum da camada muda mesmo
              assim.
            </p>
          </Card>
        </>
      ) : (
        <p className="text-sm text-[var(--muted)]">carregando dados…</p>
      )}
    </div>
  );
}
