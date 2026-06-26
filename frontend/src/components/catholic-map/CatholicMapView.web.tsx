import React, { useEffect, useMemo, useRef } from "react";
import { buildMapHtml, MapMarker } from "./mapHtml";

export type MapBounds = { south: number; west: number; north: number; east: number; zoom: number };

export default function CatholicMapView({
  markers,
  onSelect,
  onBoundsChange,
}: {
  markers: MapMarker[];
  onSelect: (id: string) => void;
  onBoundsChange?: (b: MapBounds) => void;
}) {
  // HTML is built once; markers are pushed in via postMessage so panning
  // never reloads the map tiles.
  const html = useMemo(() => buildMapHtml([]), []);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const readyRef = useRef(false);
  const markersRef = useRef(markers);
  markersRef.current = markers;

  const push = (arr: MapMarker[]) => {
    const win = iframeRef.current?.contentWindow;
    if (win) win.postMessage(JSON.stringify({ type: "setMarkers", markers: arr }), "*");
  };

  useEffect(() => {
    function handler(ev: MessageEvent) {
      try {
        const data = typeof ev.data === "string" ? JSON.parse(ev.data) : ev.data;
        if (!data) return;
        if (data.type === "selectSite" && data.id) onSelect(data.id);
        else if (data.type === "ready") {
          readyRef.current = true;
          push(markersRef.current);
        } else if (data.type === "bounds" && onBoundsChange) {
          onBoundsChange({ south: data.south, west: data.west, north: data.north, east: data.east, zoom: data.zoom });
        }
      } catch {
        /* ignore */
      }
    }
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [onSelect, onBoundsChange]);

  useEffect(() => {
    if (readyRef.current) push(markers);
  }, [markers]);

  return React.createElement("iframe", {
    ref: iframeRef,
    title: "Catholic World Map",
    srcDoc: html,
    style: { border: "none", width: "100%", height: "100%", display: "block" },
  });
}
