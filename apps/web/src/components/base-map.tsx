"use client";

/**
 * Shared MapLibre+deck.gl shell (reverse-controlled mode per deck.gl docs).
 * Layers are injected by callers via the `layers` prop; MapLibre-native
 * sources (e.g. PMTiles) can be passed as `children`.
 */

import type { LayersList, MapViewState } from "@deck.gl/core";
import { DeckGL } from "@deck.gl/react";
import { Map as ReactMap } from "react-map-gl/maplibre";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { VIEW_SJP } from "@/lib/utils";

// register the pmtiles:// protocol once so MapLibre sources can read
// single-file PMTiles archives straight from static hosting
let pmtilesRegistered = false;
async function ensurePmtilesProtocol() {
  if (pmtilesRegistered || typeof window === "undefined") return;
  const { Protocol } = await import("pmtiles");
  const protocol = new Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  pmtilesRegistered = true;
}
if (typeof window !== "undefined") void ensurePmtilesProtocol();

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
  children?: React.ReactNode;
};

export default function BaseMap({ layers, getTooltip, initialViewState, children }: BaseMapProps) {
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
        <ReactMap mapStyle={BASEMAP_STYLE as unknown as string}>{children}</ReactMap>
      </DeckGL>
    </div>
  );
}
