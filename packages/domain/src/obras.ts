import { z } from "zod";

/** Current state of one tracked ArcGIS layer, from the newest snapshot. */
export const obrasLayerState = z.object({
  slug: z.string(),
  description: z.string().default(""),
  service: z.string(),
  featureCount: z.number().int().nonnegative(),
  lastChecked: z.string().datetime({ offset: true }),
  /** snapshot date (ISO) since which the layer is unchanged */
  stableSince: z.string(),
  checksum: z.string(),
});

export type ObrasLayerState = z.infer<typeof obrasLayerState>;

/** A detected change between two consecutive snapshots. */
export const obrasEvent = z.object({
  slug: z.string(),
  description: z.string().default(""),
  from: z.string(),
  to: z.string(),
  added: z.number().int().nonnegative(),
  removed: z.number().int().nonnegative(),
  checksumFrom: z.string(),
  checksumTo: z.string(),
});

export type ObrasEvent = z.infer<typeof obrasEvent>;

export const obrasTimelineResult = z.object({
  analysis: z.literal("obras-timeline"),
  generatedAt: z.string().datetime({ offset: true }),
  snapshotsAnalyzed: z.number().int().nonnegative(),
  layers: z.array(obrasLayerState),
  events: z.array(obrasEvent),
});

export type ObrasTimelineResult = z.infer<typeof obrasTimelineResult>;
