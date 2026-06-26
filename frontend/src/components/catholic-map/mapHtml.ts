/**
 * Builds a self-contained Leaflet HTML document for the Catholic World Map.
 * Loads OpenStreetMap tiles (free, no API key) and drops a coloured marker for
 * every site. Tapping a marker posts a message to the host (React Native
 * WebView on native, or the parent window via iframe on web).
 */
export type MapMarker = {
  id: string;
  name: string;
  type: string;
  lat: number;
  lng: number;
  persecuted?: boolean;
};

const TYPE_COLORS: Record<string, string> = {
  basilica: "#D4AF37",
  cathedral: "#9C6B3F",
  shrine: "#7A86C4",
  apparition: "#3F7AC4",
  monastery: "#5B8A5B",
  church: "#B05A7A",
};

export function buildMapHtml(markers: MapMarker[]): string {
  const data = JSON.stringify(markers);
  const colors = JSON.stringify(TYPE_COLORS);
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map { height: 100%; margin: 0; padding: 0; background: #EFE7D6; }
    .leaflet-container { font-family: -apple-system, system-ui, sans-serif; }
    .pin {
      width: 18px; height: 18px; border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg); border: 2px solid #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    }
    .pin.persecuted {
      border-color: #B3261E;
      box-shadow: 0 0 0 3px rgba(179,38,30,0.35), 0 1px 3px rgba(0,0,0,0.4);
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    var MARKERS = ${data};
    var COLORS = ${colors};
    function send(id) {
      var msg = JSON.stringify({ type: 'selectSite', id: id });
      try { if (window.ReactNativeWebView) { window.ReactNativeWebView.postMessage(msg); return; } } catch (e) {}
      try { if (window.parent) { window.parent.postMessage(msg, '*'); } } catch (e) {}
    }
    var map = L.map('map', { worldCopyJump: true, zoomControl: true, attributionControl: false })
      .setView([25, 5], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, minZoom: 2,
    }).addTo(map);
    MARKERS.forEach(function (m) {
      var color = COLORS[m.type] || '#B05A7A';
      var cls = m.persecuted ? 'pin persecuted' : 'pin';
      var icon = L.divIcon({
        className: '',
        html: '<div class="' + cls + '" style="background:' + color + '"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 18],
      });
      var marker = L.marker([m.lat, m.lng], { icon: icon, title: m.name }).addTo(map);
      marker.bindTooltip(m.name, { direction: 'top', offset: [0, -16] });
      marker.on('click', function () { send(m.id); });
    });
  </script>
</body>
</html>`;
}
