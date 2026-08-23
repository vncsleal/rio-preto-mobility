import { z } from "zod";

/**
 * Metadata attached to every fetched ArcGIS layer snapshot.
 * The snapshot files themselves are GeoJSON FeatureCollections (EPSG:4326).
 */
export const layerSnapshotMeta = z.object({
  /** ArcGIS service path, e.g. "Planejamento/CICLOVIAS" */
  service: z.string(),
  layerId: z.number().int(),
  name: z.string(),
  fetchedAt: z.string().datetime({ offset: true }),
  featureCount: z.number().int().nonnegative(),
  crs: z.literal("EPSG:4326"),
  /** sha256 of the serialized geojson — used for cheap diff detection */
  checksum: z.string(),
});

export type LayerSnapshotMeta = z.infer<typeof layerSnapshotMeta>;

/** Catalog entry describing a layer we track over time. */
export const trackedLayer = z.object({
  service: z.string(),
  layerId: z.number().int(),
  slug: z.string(),
  description: z.string(),
});

export type TrackedLayer = z.infer<typeof trackedLayer>;
