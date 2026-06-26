import React, { useMemo, useRef } from "react";
import { StyleSheet, View } from "react-native";
import { WebView } from "react-native-webview";
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
  // HTML built once; markers pushed via injectJavaScript so panning never reloads tiles.
  const html = useMemo(() => buildMapHtml([]), []);
  const webRef = useRef<WebView | null>(null);
  const readyRef = useRef(false);
  const markersRef = useRef(markers);
  markersRef.current = markers;

  const push = (arr: MapMarker[]) => {
    webRef.current?.injectJavaScript(
      `try{window.__setMarkers(${JSON.stringify(arr)});}catch(e){} true;`,
    );
  };

  // Push markers whenever they change (after the map signalled ready).
  React.useEffect(() => {
    if (readyRef.current) push(markers);
  }, [markers]);

  return (
    <View style={styles.fill}>
      <WebView
        ref={webRef}
        testID="catholic-map-webview"
        originWhitelist={["*"]}
        source={{ html }}
        javaScriptEnabled
        domStorageEnabled
        onMessage={(e) => {
          try {
            const data = JSON.parse(e.nativeEvent.data);
            if (data?.type === "selectSite" && data.id) onSelect(data.id);
            else if (data?.type === "ready") {
              readyRef.current = true;
              push(markersRef.current);
            } else if (data?.type === "bounds" && onBoundsChange) {
              onBoundsChange({ south: data.south, west: data.west, north: data.north, east: data.east, zoom: data.zoom });
            }
          } catch {
            /* ignore */
          }
        }}
        style={styles.fill}
      />
    </View>
  );
}

const styles = StyleSheet.create({ fill: { flex: 1 } });
