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
