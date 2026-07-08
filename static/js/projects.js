const { createApp } = Vue;

const CENTER = [21.38866, 39.42683];
const ZOOM = 11;

async function api(method, url, body) {
  const opt = { method, headers: {} };
  if (body) {
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const res = await fetch(url, opt);
  if (!res.ok) throw new Error(await res.text());
  return res.status === 204 ? null : res.json();
}

const BRIDGE_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M2 18h20"/><path d="M3 18v-3a9 9 0 0 1 18 0v3"/><path d="M12 18v-6"/><path d="M7.5 18v-3.4"/><path d="M16.5 18v-3.4"/></svg>`;

function sqr(x) { return x * x; }
function dist2(v, w) { return sqr(v[0] - w[0]) + sqr(v[1] - w[1]); }
function distToSegmentSquared(p, v, w) {
  var l2 = dist2(v, w);
  if (l2 === 0) return dist2(p, v);
  var t = ((p[0] - v[0]) * (w[0] - v[0]) + (p[1] - v[1]) * (w[1] - v[1])) / l2;
  t = Math.max(0, Math.min(1, t));
  return dist2(p, [ v[0] + t * (w[0] - v[0]), v[1] + t * (w[1] - v[1]) ]);
}

function bridgeIconWithName(name, color) {
  return L.divIcon({
    className: "",
    html: `
      <div style="position: absolute; bottom: 38px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.75); color: #fff; padding: 3px 8px; border-radius: 6px; font-size: 11px; white-space: nowrap; font-weight: bold; border: 1px solid ${color}; pointer-events: none;">
        ${name}
      </div>
      <div class="bridge-marker" style="--bc:${color}">${BRIDGE_SVG}</div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 36]
  });
}

createApp({
  data() {
    return {
      zones: [],
      bridges: [],
      selectedZone: null,
      loading: true,
      map: null,
      polylines: [],
      bridgeMarkers: []
    };
  },
  async mounted() {
    this.initMap();
    setTimeout(async () => {
      this.map.invalidateSize();
      await this.loadData();
    }, 150);
  },
  methods: {
    initMap() {
      this.map = L.map("map", { maxZoom: 19, zoomAnimation: false, markerZoomAnimation: false }).setView(CENTER, ZOOM);
      const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        maxZoom: 19, maxNativeZoom: 17, attribution: "Holy Makkah"
      });
      const streets = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19, maxNativeZoom: 19, attribution: "© Holy Makkah"
      });
      satellite.addTo(this.map);
      L.control.layers({ "قمر صناعي": satellite, "خريطة شوارع": streets }, {}).addTo(this.map);

      window.addEventListener("resize", () => {
        if (this.map) {
          try { this.map.invalidateSize(); } catch(e) {}
        }
      });
    },
    async loadData() {
      this.loading = true;
      try {
        const [zonesRes, bridgesRes] = await Promise.all([
          api("GET", "/api/zones/"),
          api("GET", "/api/bridges/")
        ]);
        this.zones = zonesRes;
        this.bridges = bridgesRes;
        this.renderZones();
        this.renderBridges();
      } catch (e) {
        console.error("Error loading data:", e);
      } finally {
        this.loading = false;
      }
    },
    renderBridges() {
      this.bridgeMarkers.forEach(m => this.map.removeLayer(m));
      this.bridgeMarkers = [];
      this.bridges.forEach(b => {
        if (b.lat && b.lng) {
          // Find closest zone color
          let color = b.status === "critical" ? "#ef4444" : b.status === "maintenance" ? "#eab308" : b.status === "good" ? "#22c55e" : "#3b82f6";
          let closestZone = null;
          let minDistance = Infinity;
          const p = [b.lat, b.lng];
          
          this.zones.forEach(zone => {
            if (!zone.geom || zone.geom.length < 2) return;
            for (let i = 0; i < zone.geom.length - 1; i++) {
              const d = distToSegmentSquared(p, zone.geom[i], zone.geom[i+1]);
              if (d < minDistance) {
                minDistance = d;
                closestZone = zone;
              }
            }
          });

          // If bridge is within ~5km of a zone, use its color (0.002 squared = 0.000004)
          // 0.0001 squared is ~0.00000001
          // Since some bridges might be perfectly on the line, minDistance will be very close to 0.
          if (minDistance < 0.0001 && closestZone && closestZone.color) {
            color = closestZone.color;
          }

          const m = L.marker([b.lat, b.lng], {
            icon: bridgeIconWithName(b.name, color)
          }).addTo(this.map);
          this.bridgeMarkers.push(m);
        }
      });
    },
    renderZones() {
      // Clear existing polylines
      this.polylines.forEach(p => this.map.removeLayer(p));
      this.polylines = [];

      this.zones.forEach(zone => {
        if (zone.geom && zone.geom.length > 0) {
          // geom is array of [lat, lng]
          const polyline = L.polyline(zone.geom, {
            color: zone.color || '#3b82f6',
            weight: 6,
            opacity: 0.85,
          }).addTo(this.map);

          // dashed highlight line on top
          L.polyline(zone.geom, {
            color: '#fff',
            weight: 2,
            dashArray: '5, 5',
            opacity: 0.6,
            interactive: false
          }).addTo(this.map);

          polyline.on('click', () => {
            try {
              const b = polyline.getBounds();
              if (b.isValid()) this.map.fitBounds(b, { padding: [50, 50], animate: false });
            } catch(e) {}
            setTimeout(() => {
              this.selectedZone = zone;
            }, 50);
          });

          // Add tooltip (Temporarily disabled to fix latLngToLayerPoint bug)
          // polyline.bindTooltip(zone.name, { permanent: false, direction: 'center' });

          this.polylines.push(polyline);
        }
      });
      
      if (this.polylines.length > 0) {
        try {
          const group = L.featureGroup(this.polylines);
          const b = group.getBounds();
          if (b.isValid()) this.map.fitBounds(b, { padding: [50, 50], animate: false });
        } catch(e) {}
      }
    },
    closePanel() {
      this.selectedZone = null;
    }
  }
}).mount("#app");
