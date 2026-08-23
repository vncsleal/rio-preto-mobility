"use client";

/**
 * 15-minutos map: bairro choropleth by accessibility score (0..1) plus the
 * measured POIs themselves (the evidence behind the score).
 * GeoJsonLayer handles Polygon + MultiPolygon natively.
 */

import { GeoJsonLayer, ScatterplotLayer } from "@deck.gl/layers";
import type { LayersList } from "@deck.gl/core";
import BaseMap from "@/components/base-map";
import { VIEW_SJP } from "@/lib/utils";

export type BairroArea = {
  sectorId: string;
  name: string;
  score: number;
  counts?: Record<string, number>;
  reachable?: Record<string, boolean>;
};

type PoiProps = {
  category: string;
  name?: string;
};

type AreaFeature = GeoJSON.Feature<GeoJSON.MultiPolygon | GeoJSON.Polygon, BairroArea>;
type PoiFeature = GeoJSON.Feature<GeoJSON.Point, PoiProps>;

const CATEGORY_LABELS: Record<string, string> = {
  educacao: "educação",
  saude: "saúde",
  comercio: "comércio",
};

/** dot colors for the measured POIs — chosen to pop against the choropleth */
export const CATEGORY_COLORS: Record<string, [number, number, number]> = {
  educacao: [56, 189, 248], // sky
  saude: [232, 121, 249], // fuchsia
  comercio: [250, 204, 21], // yellow
};

/** rose -> amber -> emerald, gray when there is nothing reachable at all */
export function scoreColor(score: number): [number, number, number] {
  if (score <= 0) return [100, 116, 139];
  const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);
  if (score < 0.5) {
    const t = score / 0.5;
    return [lerp(251, 251, t), lerp(113, 191, t), lerp(133, 36, t)];
  }
  const t = (score - 0.5) / 0.5;
  return [lerp(251, 52, t), lerp(191, 211, t), lerp(36, 153, t)];
}

type AcessoMapProps = {
  areas: GeoJSON.FeatureCollection;
  pois?: GeoJSON.FeatureCollection;
  showPois?: boolean;
};

export default function AcessoMap({ areas, pois, showPois = true }: AcessoMapProps) {
  const areasLayer = new GeoJsonLayer<BairroArea>({
    id: "acesso-bairros",
    data: areas,
    getFillColor: (f) => {
      const p = (f as unknown as AreaFeature)?.properties;
      return [...scoreColor(p?.score ?? 0), 200];
    },
    getLineColor: [17, 22, 31],
    lineWidthMinPixels: 1,
    pickable: true,
    stroked: true,
    filled: true,
    opacity: 0.85,
  });

  const layers: LayersList = [areasLayer];

  if (showPois && pois) {
    layers.push(
      new ScatterplotLayer<PoiProps>({
        id: "acesso-pois",
        data: pois.features as unknown as PoiFeature[],
        getPosition: (f) =>
          ((f as unknown as PoiFeature).geometry?.coordinates ?? [0, 0]) as [number, number],
        getFillColor: (f) =>
          CATEGORY_COLORS[(f as unknown as PoiFeature).properties?.category] ?? [148, 163, 184],
        getLineColor: [17, 22, 31],
        stroked: true,
        lineWidthMinPixels: 1,
        radiusMinPixels: 2.5,
        radiusMaxPixels: 5,
        pickable: true,
      }),
    );
  }

  const tooltip = ({ object }: { object?: unknown }) => {
    const feature = object as AreaFeature | PoiFeature | null;
    if (!feature?.properties) return null;

    // POIs carry `category`; bairro polygons don't
    if ("category" in feature.properties && feature.geometry?.type === "Point") {
      const p = feature.properties as PoiProps;
      return {
        html: `<b>${CATEGORY_LABELS[p.category] ?? p.category}</b>${
          p.name ? `<br/>${p.name}` : ""
        }`,
        style: { backgroundColor: "#11161f", color: "#e5e7eb" },
      };
    }

    const props = feature.properties as BairroArea;
    const parts =
      props.counts &&
      Object.entries(props.counts)
        .map(([k, v]) => `${CATEGORY_LABELS[k] ?? k}: ${v}`)
        .join(" · ");
    return {
      html: `<b>${props.name || "sem nome"}</b><br/>score ${(props.score * 100).toFixed(
        0,
      )}%${parts ? `<br/>${parts}` : ""}`,
      style: { backgroundColor: "#11161f", color: "#e5e7eb" },
    };
  };

  return (
    <BaseMap layers={layers} getTooltip={tooltip} initialViewState={{ ...VIEW_SJP, zoom: 12 }} />
  );
}
