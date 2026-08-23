import { z } from "zod";

/** A ciclovia segment classified by comparing the city's official layer with OSM. */
export const gapKind = z.enum(["paper-only", "osm-only", "matched"]);

export const gapSegment = z.object({
  id: z.string(),
  kind: gapKind,
  name: z.string().default(""),
  lengthM: z.number().nonnegative(),
  source: z.enum(["city", "osm"]),
});

export type GapSegment = z.infer<typeof gapSegment>;

export const cicloviaGapResult = z.object({
  analysis: z.literal("ciclovia-gap"),
  // pipeline emits "+00:00" offsets (python isoformat), so allow them
  generatedAt: z.string().datetime({ offset: true }),
  extractDates: z.object({
    city: z.string(),
    osm: z.string(),
  }),
  matchBufferM: z.number(),
  summary: z.object({
    kmPaperOnly: z.number(),
    kmOsmOnly: z.number(),
    kmMatched: z.number(),
    segmentsPaperOnly: z.number().int(),
    segmentsOsmOnly: z.number().int(),
  }),
});

export type CicloviaGapResult = z.infer<typeof cicloviaGapResult>;
