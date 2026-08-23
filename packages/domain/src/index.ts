export * from "./layer";
export * from "./ciclovia";
export * from "./access";
export * from "./coverage";
export * from "./obras";
export * from "./projetos";
export * from "./zoneamento";

import { z } from "zod";
import { cicloviaGapResult } from "./ciclovia";
import { accessScoreResult } from "./access";
import { obrasTimelineResult } from "./obras";
import { stopCoverageResult } from "./coverage";
import { zoneamentoResult } from "./zoneamento";

/**
 * Envelope for every metrics artifact published to /public/data/metrics.
 * The web app validates payloads with this before rendering.
 */
export const analysisEnvelope = z.discriminatedUnion("analysis", [
  cicloviaGapResult,
  accessScoreResult,
  obrasTimelineResult,
  stopCoverageResult,
  zoneamentoResult,
]);

export type AnalysisEnvelope = z.infer<typeof analysisEnvelope>;
