/* ====== صفحة أصول المحور (Vue 3 + Leaflet) ====== */

const { createApp } = Vue;



const CENTER = [21.38866, 39.42683];

const ZOOM = 11;



function baseLayers() {

  const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 19, maxNativeZoom: 17, attribution: "Holy Makkah" });

  const streets = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, maxNativeZoom: 19, attribution: "© OpenStreetMap, © Holy Makkah" });

  return { satellite, streets };

}



const AXIS_POPUP_SKIP = new Set([
  "layer", "color", "name", "lat", "lng", "x", "y", "category",
  "خط الطول للنقطة", "خط العرض للنقطة",
  "خط طول البداية", "خط عرض البداية", "خط طول النهاية", "خط عرض النهاية",
  "Start_X", "Start_Y", "START_Y", "END_X", "END_Y",
]);

function axisPopupRows(p, skip = AXIS_POPUP_SKIP) {
  const row = (label, value) => value ? `<div class="axis-popup-row"><span>${label}</span><b>${value}</b></div>` : "";
  return Object.entries(p)
    .filter(([key, value]) => !skip.has(key) && value)
    .map(([key, value]) => row(key, value))
    .join("");
}

function axisPopupHtml(p) {

  const row = (label, value) => value ? `<div class="axis-popup-row"><span>${label}</span><b>${value}</b></div>` : "";

  if (p.layer === "signs") {

    return `<div class="axis-popup-title">لوحة إرشادية</div>${row("خط العرض", p.x)}${row("خط الطول", p.y)}`;

  }

  if (p.layer === "lighting") {

    const title = p.kind || p.name || "إنارة";

    const desc = (p.description || "").replace(/\n/g, "<br>");

    return `<div class="axis-popup-title">${title}</div>${desc ? `<div class="axis-popup-desc">${desc}</div>` : ""}`;

  }

  if (p.layer === "bridges") {

    const title = p.name || "جسر";

    return `<div class="axis-popup-title">${title}</div>${axisPopupRows(p)}`;

  }

  if (p.layer === "roads") {

    const title = p.name || p.category || "طريق";

    const category = p.category ? row("التصنيف", p.category) : "";

    return `<div class="axis-popup-title">${title}</div>${category}${axisPopupRows(p)}`;

  }

  return "";

}



function pointIcon(color, size = 8, shape = "circle") {

  const style = shape === "square"

    ? `width:${size}px;height:${size}px;border-radius:3px;background:${color};border:2px solid rgba(255,255,255,.9);box-shadow:0 0 0 1px rgba(0,0,0,.35)`

    : `width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid rgba(255,255,255,.85);box-shadow:0 0 0 1px rgba(0,0,0,.35)`;

  return L.divIcon({

    className: "axis-point-icon",

    iconSize: [size, size],

    iconAnchor: [size / 2, size / 2],

    html: `<span style="display:block;${style}"></span>`,

  });

}



createApp({

  data() {

    return {

      loading: true,

      filterOpen: false,

      map: null,

      roadFeatures: [],

      bridgeFeatures: [],

      lightingFeatures: [],

      signFeatures: [],

      roadsLayer: null,

      bridgesLayer: null,

      lightingLayer: null,

      signsLayer: null,

      showRoads: true,

      showBridges: true,

      showLighting: true,

      showSigns: true,

    };

  },

  computed: {

    visibleRoadCount() { return this.showRoads ? this.roadFeatures.length : 0; },

    visibleBridgeCount() { return this.showBridges ? this.bridgeFeatures.length : 0; },

    visibleLightingCount() { return this.showLighting ? this.lightingFeatures.length : 0; },

    visibleSignsCount() { return this.showSigns ? this.signFeatures.length : 0; },

    visibleTotalCount() {

      return this.visibleRoadCount + this.visibleBridgeCount

        + this.visibleLightingCount + this.visibleSignsCount;

    },

  },

  watch: {

    filterOpen() {

      setTimeout(() => { if (this.map) this.map.invalidateSize(); }, 120);

    },

    showRoads() { this.renderLayers(false); },

    showBridges() { this.renderLayers(false); },

    showLighting() { this.renderLayers(false); },

    showSigns() { this.renderLayers(false); },

  },

  async mounted() {

    this.initMap();

    setTimeout(async () => {

      this.map.invalidateSize();

      await this.load();

    }, 150);

    window.addEventListener("keydown", e => {

      if (e.key === "Escape" && this.filterOpen) this.filterOpen = false;

    });

    window.addEventListener("resize", () => { if (this.map) this.map.invalidateSize(); });

  },

  methods: {

    initMap() {

      this.map = L.map("map", { zoomControl: false, maxZoom: 19, zoomAnimation: false, markerZoomAnimation: false }).setView(CENTER, ZOOM);

      L.control.zoom({ position: "topleft" }).addTo(this.map);

      const { satellite, streets } = baseLayers();

      satellite.addTo(this.map);

      L.control.layers({ "قمر صناعي": satellite, "خريطة شوارع": streets }, {}, { position: "topleft" }).addTo(this.map);

    },

    async load() {

      try {

        const [roadsRes, bridgesRes, lightingRes, signsRes] = await Promise.all([

          fetch("/static/data/axis-roads.geojson"),

          fetch("/static/data/axis-bridges.geojson"),

          fetch("/static/data/axis-lighting.geojson"),

          fetch("/static/data/axis-signs.geojson"),

        ]);

        const [roads, bridges, lighting, signs] = await Promise.all([

          roadsRes.json(),

          bridgesRes.json(),

          lightingRes.json(),

          signsRes.json(),

        ]);

        this.roadFeatures = roads.features || [];

        this.bridgeFeatures = bridges.features || [];

        this.lightingFeatures = lighting.features || [];

        this.signFeatures = signs.features || [];

        this.renderLayers(true);

      } catch (e) {

        console.error("axis assets load failed", e);

      } finally {

        this.loading = false;

      }

    },

    resetAxisFilters() {

      this.showRoads = true;

      this.showBridges = true;

      this.showLighting = true;

      this.showSigns = true;

      this.renderLayers(false);

    },

    clearLayer(name) {

      if (this[name]) {

        this.map.removeLayer(this[name]);

        this[name] = null;

      }

    },

    renderLayers(fit = false) {

      if (!this.map) return;

      this.clearLayer("roadsLayer");

      this.clearLayer("bridgesLayer");

      this.clearLayer("lightingLayer");

      this.clearLayer("signsLayer");



      const boundsLayers = [];



      if (this.showRoads && this.roadFeatures.length) {

        this.roadsLayer = L.geoJSON({ type: "FeatureCollection", features: this.roadFeatures }, {

          style: (f) => {

            const geom = f.geometry && f.geometry.type;

            const isLine = geom === "LineString" || geom === "Polygon" || geom === "MultiPolygon";

            if (!isLine) return {};

            const color = (f.properties && f.properties.color) || "#38bdf8";

            const category = (f.properties && f.properties.category) || "";

            return {

              color,

              weight: category === "البردورات" ? 3 : 2,

              opacity: 0.95,

              fillColor: color,

              fillOpacity: category === "الأرصفة" ? 0.3 : 0.15,

            };

          },

          pointToLayer: (feature, latlng) => L.marker(latlng, {

            icon: pointIcon((feature.properties && feature.properties.color) || "#38bdf8", 10, "square"),

          }),

          onEachFeature: (feature, layer) => {

            layer.bindPopup(axisPopupHtml(feature.properties || {}), { className: "axis-popup", maxWidth: 280 });

          },

        }).addTo(this.map);

        boundsLayers.push(this.roadsLayer);

      }



      if (this.showBridges && this.bridgeFeatures.length) {

        this.bridgesLayer = L.geoJSON({ type: "FeatureCollection", features: this.bridgeFeatures }, {

          pointToLayer: (feature, latlng) => L.marker(latlng, {

            icon: pointIcon((feature.properties && feature.properties.color) || "#c084fc", 10, "square"),

          }),

          onEachFeature: (feature, layer) => {

            layer.bindPopup(axisPopupHtml(feature.properties || {}), { className: "axis-popup", maxWidth: 280 });

          },

        }).addTo(this.map);

        boundsLayers.push(this.bridgesLayer);

      }



      if (this.showLighting && this.lightingFeatures.length) {

        this.lightingLayer = L.geoJSON({ type: "FeatureCollection", features: this.lightingFeatures }, {

          style: (f) => {

            const isLine = f.geometry && f.geometry.type === "LineString";

            return {

              color: (f.properties && f.properties.color) || "#fbbf24",

              weight: isLine ? 3 : 0,

              opacity: 0.9,

              dashArray: isLine ? "6 4" : null,

            };

          },

          pointToLayer: (feature, latlng) => L.marker(latlng, {

            icon: pointIcon((feature.properties && feature.properties.color) || "#fde047", 7),

          }),

          onEachFeature: (feature, layer) => {

            layer.bindPopup(axisPopupHtml(feature.properties || {}), { className: "axis-popup", maxWidth: 280 });

          },

        }).addTo(this.map);

        boundsLayers.push(this.lightingLayer);

      }



      if (this.showSigns && this.signFeatures.length) {

        this.signsLayer = L.geoJSON({ type: "FeatureCollection", features: this.signFeatures }, {

          pointToLayer: (feature, latlng) => L.marker(latlng, {

            icon: pointIcon((feature.properties && feature.properties.color) || "#fb923c", 9),

          }),

          onEachFeature: (feature, layer) => {

            layer.bindPopup(axisPopupHtml(feature.properties || {}), { className: "axis-popup", maxWidth: 240 });

          },

        }).addTo(this.map);

        boundsLayers.push(this.signsLayer);

      }



      if (fit && boundsLayers.length) {

        try {

          const group = L.featureGroup(boundsLayers);

          this.map.fitBounds(group.getBounds(), { padding: [60, 70], maxZoom: 14, animate: false });

        } catch (e) {}

      }

    },

    zoomToAxis() {

      const layers = [this.roadsLayer, this.bridgesLayer, this.lightingLayer, this.signsLayer].filter(Boolean);

      if (!layers.length) return;

      try {

        const group = L.featureGroup(layers);

        this.map.fitBounds(group.getBounds(), { padding: [60, 70], maxZoom: 16, animate: false });

      } catch (e) {}

    },

  },

}).mount("#app");

