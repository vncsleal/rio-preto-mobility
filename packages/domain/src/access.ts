import { z } from "zod";

/**
 * 15-minute accessibility score for one census sector (IBGE 2022).
 * Produced by pipeline/compile/access_score.py.
 */
export const accessScore = z.object({
  sectorId: z.string(),
  bairro: z.string().default(""),
  /** null until the IBGE Censo job lands */
  population: z.number().int().nonnegative().nullable(),
  meanIncome: z.number().nullable(),
  /** share of key POI categories reachable on foot within the time budget (0..1) */
  score: z.number().min(0).max(1),
  reachable: z.record(z.string(), z.boolean()),
  /** optional detail: POIs reachable per category, uncapped counts */
  counts: z.record(z.string(), z.number()).optional(),
});

export type AccessScore = z.infer<typeof accessScore>;

export const accessScoreResult = z.object({
  analysis: z.literal("access-score"),
  generatedAt: z.string().datetime({ offset: true }),
  /** censo value is the IBGE release date (YYYYMMDD) or "pendente" */
  extractDates: z.object({ osm: z.string(), censo: z.string() }),
  timeBudgetMin: z.number(),
  summary: z.object({
    meanScore: z.number(),
    worstSectorId: z.string().nullable(),
    bestSectorId: z.string().nullable(),
    bairroCount: z.number().int().nonnegative().optional(),
    /** sum of Censo 2022 population attributed to the evaluated bairros */
    populationTotal: z.number().int().nonnegative().optional(),
    /** census sectors successfully matched to a bairro */
    setoresCenso: z.number().int().nonnegative().optional(),
  }),
  scores: z.array(accessScore),
});

export type AccessScoreResult = z.infer<typeof accessScoreResult>;
