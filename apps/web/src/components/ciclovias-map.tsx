"use client";

/**
 * Ciclovias map: gap segments as colored lines.
 * Data contract lives in @rio-preto/domain (Zod-validated upstream).
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import BaseMap from "@/components/base-map";
import { VIEW_SJP } from "@/lib/utils";

export const GAP_COLORS: Record<string, [number, number, number]> = {
  "paper-only": [251, 113, 133], // rose — existe só no papel
  "osm-only": [251, 191, 36], // amber — mapeada só no OSM
  matched: [52, 211, 153], // emerald — confirmada nas duas fontes
};

export const GAP_LABELS: Record<string, string> = {
  "paper-only": "só no papel",
  "osm-only": "só no OSM",
  matched: "confirmada nas duas fontes",
};

type SegmentProps = {
  kind: string;
  name?: string;
  lengthM?: number;
  source?: string;
};

type SegmentFeature = GeoJSON.Feature<GeoJSON.LineString, SegmentProps>;

export default function CicloviasMap({ segments }: { segments: GeoJSON.FeatureCollection }) {
  const layer = new GeoJsonLayer<SegmentProps>({
    id: "gap-segments",
    data: segments,
    getLineColor: (f) => GAP_COLORS[(f as SegmentFeature).properties?.kind] ?? [148, 163, 184],
    getLineWidth: 2.5,
    lineWidthUnits: "pixels",
    pickable: true,
    stroked: false,
    filled: false,
  });

  const tooltip = ({ object }: { object?: unknown }) => {
    const props = (object as SegmentFeature | null)?.properties;
    if (!props) return null;
    const name =
      props.name && !/^\s*nan\s*$/i.test(props.name) ? props.name : "sem nome";
    const kind = GAP_LABELS[props.kind] ?? props.kind;
    return {
      html: `<b>${kind}</b><br/>${name} · ${Math.round(props.lengthM ?? 0)} m`,
      style: { backgroundColor: "#11161f", color: "#e5e7eb" },
    };
  };

  return <BaseMap layers={[layer]} getTooltip={tooltip} initialViewState={VIEW_SJP} />;
}
