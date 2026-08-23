"use client";

/**
 * Zoneamento map: bairro choropleth by parcel count (cadastral density)
 * + macrozone outlines. Non-urban macrozones get a hatched-feel via color.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import type { LayersList } from "@deck.gl/core";
import BaseMap from "@/components/base-map";
import { VIEW_SJP } from "@/lib/utils";

export type ZonaArea = {
  sectorId: string;
  name: string;
  parcels: number;
  areaHa: number;
  dominantZone?: string | null;
  topZonas?: Record<string, number>;
  macrozona?: string | null;
};

type MacroFeature = GeoJSON.Feature<GeoJSON.MultiPolygon | GeoJSON.Polygon, {
  name: string;
  naoUrbana: boolean;
}>;

type AreaFeature = GeoJSON.Feature<GeoJSON.MultiPolygon | GeoJSON.Polygon, ZonaArea>;

const MACRO_COLORS: Record<string, [number, number, number]> = {
  Expansao: [251, 146, 60], // orange
  Protecao: [52, 211, 153], // emerald
  Restricao: [248, 113, 113], // red
  Consolidada: [96, 165, 250], // blue
  "Ocupacao Controlada": [167, 139, 250], // violet
};

/** slate -> amber -> rose by parcel density (log-ish buckets) */
export function densityColor(parcels: number): [number, number, number] {
  if (parcels <= 0) return [100, 116, 139];
  const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);
  const t = Math.min(1, Math.log10(parcels + 1) / Math.log10(2000));
  return [lerp(253, 190, t), lerp(230, 18, t), lerp(224, 60, t)];
}

const fmt = (n: number) => n.toLocaleString("pt-BR");

type ZoneamentoMapProps = {
  areas: GeoJSON.FeatureCollection;
  macros: GeoJSON.FeatureCollection;
};

export default function ZoneamentoMap({ areas, macros }: ZoneamentoMapProps) {
  const macroLayer = new GeoJsonLayer({
    id: "macrozonas",
    data: macros,
    getLineColor: (f) =>
      MACRO_COLORS[(f as unknown as MacroFeature).properties?.name] ?? [148, 163, 184],
    getFillColor: [0, 0, 0, 0],
    lineWidthMinPixels: 2,
    stroked: true,
    filled: false,
    pickable: false,
  });

  const areasLayer = new GeoJsonLayer<ZonaArea>({
    id: "zona-bairros",
    data: areas,
    getFillColor: (f) => [...densityColor((f as unknown as AreaFeature)?.properties?.parcels ?? 0), 170],
    getLineColor: [17, 22, 31],
    lineWidthMinPixels: 1,
    pickable: true,
    stroked: true,
    filled: true,
    opacity: 0.8,
  });

  const tooltip = ({ object }: { object?: unknown }) => {
    const props = (object as AreaFeature | null)?.properties;
    if (!props) return null;
    const mix = props.topZonas
      ? Object.entries(props.topZonas)
          .map(([z, n]) => `zona ${z}: ${fmt(n)}`)
          .join(" · ")
      : "";
    return {
      html: `<b>${props.name || "sem nome"}</b>${
        props.macrozona ? `<br/>macrozona: ${props.macrozona}` : ""
      }<br/>${fmt(props.parcels)} parcelas · ${props.areaHa.toLocaleString("pt-BR")} ha${
        props.dominantZone ? `<br/>zona dominante: ${props.dominantZone}` : ""
      }${mix ? `<br/>${mix}` : ""}`,
      style: { backgroundColor: "#11161f", color: "#e5e7eb" },
    };
  };

  const layers: LayersList = [areasLayer, macroLayer];
  return <BaseMap layers={layers} getTooltip={tooltip} initialViewState={{ ...VIEW_SJP, zoom: 11 }} />;
}
