"use client";

/**
 * Shared MapLibre+deck.gl shell (reverse-controlled mode per deck.gl docs).
 * Layers are injected by callers via the `layers` prop.
 */

import type { LayersList, MapViewState } from "@deck.gl/core";
import { DeckGL } from "@deck.gl/react";
import { Map as ReactMap } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { VIEW_SJP } from "@/lib/utils";

export const BASEMAP_STYLE = {
  version: 8,
  sources: {
    carto: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
      ],
      tileSize: 256,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/">CARTO</a>',
    },
  },
  layers: [{ id: "carto", type: "raster", source: "carto" }],
} as const;

export type TooltipContent = { html: string } | null;

type BaseMapProps = {
  layers: LayersList;
  getTooltip?: (info: { object?: unknown }) => TooltipContent;
  initialViewState?: Partial<MapViewState>;
};

export default function BaseMap({ layers, getTooltip, initialViewState }: BaseMapProps) {
  return (
    <div className="relative h-[540px] w-full overflow-hidden rounded-xl border border-[var(--border)]">
      <DeckGL
        initialViewState={{ ...VIEW_SJP, ...initialViewState }}
        controller
        getTooltip={getTooltip}
        layers={layers}
        style={{
          position: "absolute",
          top: "0",
          left: "0",
          width: "100%",
          height: "100%",
        }}
      >
        <ReactMap mapStyle={BASEMAP_STYLE as unknown as string} />
      </DeckGL>
    </div>
  );
}
