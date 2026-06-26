import React, { useEffect, useMemo } from "react";
import { buildMapHtml, MapMarker } from "./mapHtml";

export default function CatholicMapView({
  markers,
  onSelect,
}: {
  markers: MapMarker[];
  onSelect: (id: string) => void;
}) {
  const html = useMemo(() => buildMapHtml(markers), [markers]);

  useEffect(() => {
    function handler(ev: MessageEvent) {
      try {
        const data = typeof ev.data === "string" ? JSON.parse(ev.data) : ev.data;
        if (data?.type === "selectSite" && data.id) onSelect(data.id);
      } catch {
        /* ignore */
      }
    }
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [onSelect]);

  return React.createElement("iframe", {
    title: "Catholic World Map",
    srcDoc: html,
    style: { border: "none", width: "100%", height: "100%", display: "block" },
  });
}
