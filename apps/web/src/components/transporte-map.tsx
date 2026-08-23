"use client";

/**
 * Transporte map: bairro choropleth by stop coverage share (0..1) plus the
 * OSM bus stops themselves. Gray = no population/coverage data.
 */

import { GeoJsonLayer, ScatterplotLayer } from "@deck.gl/layers";
import type { LayersList } from "@deck.gl/core";
import BaseMap from "@/components/base-map";
import { VIEW_SJP } from "@/lib/utils";

export type CoberturaArea = {
  sectorId: string;
  name: string;
  coverageShare: number;
  population: number;
  meanIncome?: number;
};

type StopProps = {
  osm_id: number;
  name?: string;
  source_tag?: string;
};

type AreaFeature = GeoJSON.Feature<GeoJSON.MultiPolygon | GeoJSON.Polygon, CoberturaArea>;
type StopFeature = GeoJSON.Feature<GeoJSON.Point, StopProps>;

/** slate -> amber -> emerald, mirroring the 15-min score ramp */
export function coverageColor(share: number): [number, number, number] {
  if (share <= 0) return [100, 116, 139];
  const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);
  if (share < 0.5) {
    const t = share / 0.5;
    return [lerp(251, 251, t), lerp(191, 36, t), lerp(119, 36, t)];
  }
  const t = (share - 0.5) / 0.5;
  return [lerp(251, 52, t), lerp(36, 211, t), lerp(36, 153, t)];
}

const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

type TransporteMapProps = {
  areas: GeoJSON.FeatureCollection;
  stops: GeoJSON.FeatureCollection;
};

export default function TransporteMap({ areas, stops }: TransporteMapProps) {
  const areasLayer = new GeoJsonLayer<CoberturaArea>({
    id: "cobertura-bairros",
    data: areas,
    getFillColor: (f) => [...coverageColor((f as unknown as AreaFeature)?.properties?.coverageShare ?? 0), 200],
    getLineColor: [17, 22, 31],
    lineWidthMinPixels: 1,
    pickable: true,
    stroked: true,
    filled: true,
    opacity: 0.85,
  });

  const stopsLayer = new ScatterplotLayer<StopProps>({
    id: "paradas",
    data: stops.features as unknown as StopFeature[],
    getPosition: (f) =>
      ((f as unknown as StopFeature).geometry?.coordinates ?? [0, 0]) as [number, number],
    getFillColor: [59, 130, 246], // blue — stands out against the warm ramp
    getLineColor: [17, 22, 31],
    stroked: true,
    lineWidthMinPixels: 1,
    radiusMinPixels: 3,
    radiusMaxPixels: 5,
    pickable: true,
  });

  const tooltip = ({ object }: { object?: unknown }) => {
    const feature = object as AreaFeature | StopFeature | null;
    if (!feature?.properties) return null;

    if ("osm_id" in feature.properties && feature.geometry?.type === "Point") {
      const p = feature.properties as StopProps;
      return {
        html: `<b>parada</b>${p.name ? `<br/>${p.name}` : ""}`,
        style: { backgroundColor: "#11161f", color: "#e5e7eb" },
      };
    }

    const props = feature.properties as CoberturaArea;
    const renda =
      typeof props.meanIncome === "number" ? `<br/>renda média: ${brl(props.meanIncome)}` : "";
    return {
      html: `<b>${props.name || "sem nome"}</b><br/>${(
        props.coverageShare * 100
      ).toFixed(0)}% da população a ≤400 m de parada<br/>população: ${props.population.toLocaleString("pt-BR")}${renda}`,
      style: { backgroundColor: "#11161f", color: "#e5e7eb" },
    };
  };

  const layers: LayersList = [areasLayer, stopsLayer];
  return (
    <BaseMap layers={layers} getTooltip={tooltip} initialViewState={{ ...VIEW_SJP, zoom: 12 }} />
  );
}
