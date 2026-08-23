import { z } from "zod";

/** One zoning category from the municipal cadastre (analysis 5). */
export const zonaTally = z.object({
  zona: z.string(),
  parcelas: z.number().int().nonnegative(),
  areaHa: z.number().nonnegative(),
});

export type ZonaTally = z.infer<typeof zonaTally>;

/**
 * Cadastral pressure inside a macrozone: parcels whose bairro centroid
 * falls in the zone. Parcel geometry is withheld by the city's server,
 * so this is a bairro-level attribution, not a parcel-level overlay.
 */
export const macrozonaPressure = z.object({
  name: z.string(),
  poligonos: z.number().int().nonnegative(),
  areaKm2: z.number().nonnegative(),
  populacaoDeclarada: z.number().int().nonnegative().nullable(),
  bairros: z.number().int().nonnegative(),
  parcelas: z.number().int().nonnegative(),
  areaParcelasHa: z.number().nonnegative(),
  naoUrbana: z.boolean(),
});

export type MacrozonaPressure = z.infer<typeof macrozonaPressure>;

export const zoneamentoResult = z.object({
  analysis: z.literal("zoneamento-mosaico"),
  generatedAt: z.string().datetime({ offset: true }),
  /** snapshot date the parcels were extracted from */
  extractDate: z.string(),
  summary: z.object({
    parcelas: z.number().int().nonnegative(),
    parcelasSemZona: z.number().int().nonnegative(),
    /** parcels where ZONA and ZONEAMENTO attributes disagree */
    zonaDivergente: z.number().int().nonnegative(),
    categoriasZona: z.number().int().nonnegative(),
    areaTotalHa: z.number().nonnegative(),
    bairroMatch: z.object({
      matched: z.number().int().nonnegative(),
      unmatched: z.number().int().nonnegative(),
    }),
    parcelasMacrozonaNaoUrbana: z.number().int().nonnegative().optional(),
    haMacrozonaNaoUrbana: z.number().nonnegative().optional(),
  }),
  porZona: z.array(zonaTally),
  macrozonas: z.array(macrozonaPressure).default([]),
});

export type ZoneamentoResult = z.infer<typeof zoneamentoResult>;
