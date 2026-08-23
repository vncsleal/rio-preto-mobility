import { z } from "zod";

/**
 * One obra from the city's construction registry (Hosted/Obras_MapLayer),
 * normalized by pipeline/compile/obras_projetos.py.
 */
export const obrasProject = z.object({
  id: z.string(),
  finalidade: z.string(),
  status: z.string(),
  statusLabel: z.string(),
  inicio: z.string().datetime({ offset: true }).nullable(),
  terminoPrevisto: z.string().datetime({ offset: true }).nullable(),
  custo: z.number().nullable(),
  origemRecurso: z.string().nullable(),
  construtora: z.string().nullable(),
  secretaria: z.string().nullable(),
  lon: z.number().nullable(),
  lat: z.number().nullable(),
});

export type ObrasProject = z.infer<typeof obrasProject>;

export const obrasProjectsResult = z.object({
  analysis: z.literal("obras-projetos"),
  generatedAt: z.string().datetime({ offset: true }),
  /** snapshot date (ISO) the projects were extracted from */
  extractDate: z.string(),
  summary: z.object({
    total: z.number().int().nonnegative(),
    porStatus: z.record(z.string(), z.number().int().nonnegative()),
    custoPorStatus: z.record(z.string(), z.number()),
    atrasadas: z.number().int().nonnegative(),
  }),
  projetos: z.array(obrasProject),
});

export type ObrasProjectsResult = z.infer<typeof obrasProjectsResult>;
