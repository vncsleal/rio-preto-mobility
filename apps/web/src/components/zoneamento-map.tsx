"use client";

/**
 * Zoneamento map: bairro choropleth by parcel count (cadastral density)
 * + macrozone outlines. Non-urban macrozones get a hatched-feel via color.
 */

import { GeoJsonLayer } from "@deck.gl/layers";
import type { LayersList } from "@deck.gl/core";
import { Source, Layer as MapLayer } from "react-map-gl/maplibre";
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

/** slate -> amber -> rose by parcel count; power scale spreads the common
 *  100–600 range instead of saturating like log10 did */
export function densityColor(parcels: number): [number, number, number] {
  if (parcels <= 0) return [100, 116, 139];
  const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);
  const t = Math.min(1, Math.pow(parcels / 1200, 0.6));
  return [lerp(253, 190, t), lerp(230, 18, t), lerp(224, 60, t)];
}

const fmt = (n: number) => n.toLocaleString("pt-BR");

type ZoneamentoMapProps = {
  areas: GeoJSON.FeatureCollection;
  macros: GeoJSON.FeatureCollection;
  /** quadras fiscais via PMTiles (optional context layer) */
  showQuadras?: boolean;
};

const QUADRAS_URL = "pmtiles:///data/tiles/quadras.pmtiles";

export default function ZoneamentoMap({ areas, macros, showQuadras = false }: ZoneamentoMapProps) {
  const macroLayer = new GeoJsonLayer({
    id: "macrozonas",
    data: macros,
    getLineColor: (f) => {
      const base =
        MACRO_COLORS[(f as unknown as MacroFeature).properties?.name] ?? [148, 163, 184];
      return [...base, 150];
    },
    getFillColor: [0, 0, 0, 0],
    lineDash: [4, 3],
    lineWidthMinPixels: 1,
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
      }${
        props.parcels > 0
          ? `<br/>${fmt(props.parcels)} parcelas · ${props.areaHa.toLocaleString("pt-BR")} ha`
          : `<br/><i>sem vínculo cadastral</i>`
      }${
        props.parcels > 0 && props.dominantZone ? `<br/>zona dominante: ${props.dominantZone}` : ""
      }${mix ? `<br/>${mix}` : ""}`,
      style: { backgroundColor: "#11161f", color: "#e5e7eb" },
    };
  };

  // macrozone outlines render UNDER the choropleth so they read as context,
  // not as the subject of the map
  const layers: LayersList = [macroLayer, areasLayer];
  return (
    <BaseMap layers={layers} getTooltip={tooltip} initialViewState={{ ...VIEW_SJP, zoom: 11 }}>
      {showQuadras && (
        <Source id="quadras-pmtiles" type="vector" url={QUADRAS_URL}>
          <MapLayer
            id="quadras-fill"
            type="fill"
            source-layer="quadras"
            paint={{ "fill-color": "#94a3b8", "fill-opacity": 0.12 }}
          />
          <MapLayer
            id="quadras-line"
            type="line"
            source-layer="quadras"
            paint={{
              "line-color": "#475569",
              "line-opacity": 0.35,
              "line-width": ["interpolate", ["linear"], ["zoom"], 11, 0.3, 15, 1.2],
            }}
          />
        </Source>
      )}
    </BaseMap>
  );
}
