import React, { useMemo } from "react";
import { StyleSheet, View } from "react-native";
import { WebView } from "react-native-webview";
import { buildMapHtml, MapMarker } from "./mapHtml";

export default function CatholicMapView({
  markers,
  onSelect,
}: {
  markers: MapMarker[];
  onSelect: (id: string) => void;
}) {
  const html = useMemo(() => buildMapHtml(markers), [markers]);
  return (
    <View style={styles.fill}>
      <WebView
        testID="catholic-map-webview"
        originWhitelist={["*"]}
        source={{ html }}
        javaScriptEnabled
        domStorageEnabled
        onMessage={(e) => {
          try {
            const data = JSON.parse(e.nativeEvent.data);
            if (data?.type === "selectSite" && data.id) onSelect(data.id);
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
