/**
 * Builds a self-contained Leaflet HTML document for the Catholic World Map.
 * Loads OpenStreetMap tiles (free, no API key) and clusters markers for
 * performance. The host (React Native WebView / web iframe) can:
 *   - push a fresh marker set at any time via window.__setMarkers([...])
 *   - receive { type: 'selectSite', id } when a marker is tapped
 *   - receive { type: 'bounds', south, west, north, east, zoom } on move/zoom
 * so it can fetch the churches visible in the current viewport.
 */
export type MapMarker = {
  id: string;
  name: string;
  type: string;
  lat: number;
  lng: number;
  persecuted?: boolean;
  osm?: boolean;
};

const TYPE_COLORS: Record<string, string> = {
  basilica: "#D4AF37",
  cathedral: "#9C6B3F",
  shrine: "#7A86C4",
  apparition: "#3F7AC4",
  monastery: "#5B8A5B",
  church: "#B05A7A",
};

export function buildMapHtml(initialMarkers: MapMarker[]): string {
  const data = JSON.stringify(initialMarkers);
  const colors = JSON.stringify(TYPE_COLORS);
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
  <style>
    html, body, #map { height: 100%; margin: 0; padding: 0; background: #EFE7D6; }
    .leaflet-container { font-family: -apple-system, system-ui, sans-serif; }
    .pin {
      width: 16px; height: 16px; border-radius: 50% 50% 50% 0;
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
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <script>
    var COLORS = ${colors};
    function send(obj) {
      var msg = JSON.stringify(obj);
      try { if (window.ReactNativeWebView) { window.ReactNativeWebView.postMessage(msg); return; } } catch (e) {}
      try { if (window.parent) { window.parent.postMessage(msg, '*'); } } catch (e) {}
    }
    var map = L.map('map', { worldCopyJump: true, zoomControl: true, attributionControl: false })
      .setView([25, 5], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, minZoom: 2 }).addTo(map);

    var cluster = L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 50, disableClusteringAtZoom: 16 });
    map.addLayer(cluster);

    function makeIcon(m) {
      var color = COLORS[m.type] || '#B05A7A';
      var cls = m.persecuted ? 'pin persecuted' : 'pin';
      return L.divIcon({
        className: '',
        html: '<div class="' + cls + '" style="background:' + color + '"></div>',
        iconSize: [16, 16], iconAnchor: [8, 16],
      });
    }

    window.__setMarkers = function (arr) {
      cluster.clearLayers();
      var layers = [];
      for (var i = 0; i < arr.length; i++) {
        var m = arr[i];
        if (m.lat == null || m.lng == null) continue;
        var mk = L.marker([m.lat, m.lng], { icon: makeIcon(m), title: m.name });
        mk.bindTooltip(m.name, { direction: 'top', offset: [0, -14] });
        (function (id) { mk.on('click', function () { send({ type: 'selectSite', id: id }); }); })(m.id);
        layers.push(mk);
      }
      cluster.addLayers(layers);
    };

    function emitBounds() {
      var b = map.getBounds();
      send({
        type: 'bounds',
        south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast(),
        zoom: map.getZoom(),
      });
    }
    var t = null;
    map.on('moveend', function () { clearTimeout(t); t = setTimeout(emitBounds, 350); });

    // Listen for marker pushes from the host (web iframe path).
    window.addEventListener('message', function (ev) {
      try {
        var d = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data;
        if (d && d.type === 'setMarkers' && d.markers) window.__setMarkers(d.markers);
      } catch (e) {}
    });

    // Initial paint + first bounds emit.
    window.__setMarkers(${data});
    setTimeout(function () { send({ type: 'ready' }); emitBounds(); }, 300);
  </script>
</body>
</html>`;
}
