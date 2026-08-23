import { z } from "zod";

/** Bus stop coverage per census sector (analysis 4). */
export const stopCoverage = z.object({
  sectorId: z.string(),
  bairro: z.string().default(""),
  population: z.number().int().nonnegative(),
  meanIncome: z.number().nullable(),
  popWithin400m: z.number().int().nonnegative(),
  coverageShare: z.number().min(0).max(1),
});

export type StopCoverage = z.infer<typeof stopCoverage>;

/** City-wide result of the pre-GTFS stop coverage analysis (analysis 4). */
export const stopCoverageResult = z.object({
  analysis: z.literal("stop-coverage"),
  generatedAt: z.string().datetime({ offset: true }),
  /** osm value identifies the stop source ("overpass" or the GTFS filename) */
  extractDates: z.object({ osm: z.string(), censo: z.string() }),
  /** "osm" while the official GTFS is unavailable, "gtfs" once it lands */
  source: z.string().optional(),
  radiusM: z.number(),
  summary: z.object({
    stopsTotal: z.number().int().nonnegative(),
    popTotal: z.number().int().nonnegative(),
    popCoberta: z.number().int().nonnegative(),
    /** share of population living within radiusM of a mapped stop (0..1) */
    coberturaMedia: z.number().min(0).max(1),
    /** mean bairro coverage by income tercile — the equity read */
    porTercilRenda: z
      .object({
        baixa: z.number().min(0).max(1),
        media: z.number().min(0).max(1),
        alta: z.number().min(0).max(1),
      })
      .optional(),
  }),
  coberturas: z.array(stopCoverage),
});

export type StopCoverageResult = z.infer<typeof stopCoverageResult>;

/** Weekly diff between two ArcGIS snapshots of the same layer (analysis 3). */
export const snapshotDiff = z.object({
  service: z.string(),
  layerId: z.number().int(),
  from: z.string(),
  to: z.string(),
  addedFeatures: z.array(z.unknown()),
  removedFeatures: z.array(z.unknown()),
  checksumFrom: z.string(),
  checksumTo: z.string(),
});

export type SnapshotDiff = z.infer<typeof snapshotDiff>;
