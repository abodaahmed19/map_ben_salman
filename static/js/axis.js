/* ====== صفحة أصول المحور (Vue 3 + Leaflet) ====== */
const { createApp } = Vue;

const CENTER = [21.38866, 39.42683];
const ZOOM = 11;

function baseLayers() {
  const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 19, maxNativeZoom: 17, attribution: "Holy Makkah" });
  const streets = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, maxNativeZoom: 19, attribution: "© OpenStreetMap, © Holy Makkah" });
  return { satellite, streets };
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
  return `<div class="axis-popup-title">${p.segment_code || p.name || "مقطع"}</div>
    ${row("البلدية", p.municipality)}
    ${row("الحي", p.district)}
    ${row("الحي الفرعي", p.sub_district)}
    ${row("من", p.from_street)}
    ${row("إلى", p.to_street)}
    ${row("الطول", p.length_m ? `${Number(p.length_m).toFixed(1)} م` : "")}
    ${row("العرض", p.width_m ? `${p.width_m} م` : "")}`;
}

function pointIcon(color, size = 8) {
  return L.divIcon({
    className: "axis-point-icon",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid rgba(255,255,255,.85);box-shadow:0 0 0 1px rgba(0,0,0,.35)"></span>`,
  });
}

createApp({
  data() {
    return {
      loading: true,
      filterOpen: true,
      map: null,
      roadFeatures: [],
      lightingFeatures: [],
      signFeatures: [],
      roadsLayer: null,
      lightingLayer: null,
      signsLayer: null,
      showRoads: true,
      showLighting: true,
      showSigns: true,
      aMunicipality: "",
      aDistrict: "",
    };
  },
  computed: {
    filteredRoadFeatures() {
      return this.roadFeatures.filter(f => this.roadFeatureMatches(f.properties || {}));
    },
    visibleRoadCount() { return this.showRoads ? this.filteredRoadFeatures.length : 0; },
    visibleLightingCount() { return this.showLighting ? this.lightingFeatures.length : 0; },
    visibleSignsCount() { return this.showSigns ? this.signFeatures.length : 0; },
    visibleTotalCount() {
      return this.visibleRoadCount + this.visibleLightingCount + this.visibleSignsCount;
    },
    axisMunicipalities() {
      const set = new Set();
      this.roadFeatures.forEach(f => {
        const p = f.properties || {};
        if (p.municipality) set.add(p.municipality);
      });
      return [...set].sort();
    },
    axisDistricts() {
      const set = new Set();
      this.roadFeatures.forEach(f => {
        const p = f.properties || {};
        if (this.aMunicipality && p.municipality !== this.aMunicipality) return;
        if (p.district) set.add(p.district);
      });
      return [...set].sort();
    },
  },
  watch: {
    showRoads() { this.renderLayers(false); },
    showLighting() { this.renderLayers(false); },
    showSigns() { this.renderLayers(false); },
    aMunicipality() { this.onAxisMunicipalityChange(); },
    aDistrict() { this.onAxisFilterChange(); },
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
        const [roadsRes, lightingRes, signsRes] = await Promise.all([
          fetch("/static/data/axis-roads.geojson"),
          fetch("/static/data/axis-lighting.geojson"),
          fetch("/static/data/axis-signs.geojson"),
        ]);
        const [roads, lighting, signs] = await Promise.all([
          roadsRes.json(),
          lightingRes.json(),
          signsRes.json(),
        ]);
        this.roadFeatures = roads.features || [];
        this.lightingFeatures = lighting.features || [];
        this.signFeatures = signs.features || [];
        this.renderLayers(true);
      } catch (e) {
        console.error("axis assets load failed", e);
      } finally {
        this.loading = false;
      }
    },
    roadFeatureMatches(p) {
      if (this.aMunicipality && p.municipality !== this.aMunicipality) return false;
      if (this.aDistrict && p.district !== this.aDistrict) return false;
      return true;
    },
    onAxisMunicipalityChange() {
      if (this.aDistrict && !this.axisDistricts.includes(this.aDistrict)) this.aDistrict = "";
      this.onAxisFilterChange();
    },
    onAxisFilterChange() {
      this.renderLayers(false);
    },
    resetAxisFilters() {
      this.showRoads = true;
      this.showLighting = true;
      this.showSigns = true;
      this.aMunicipality = "";
      this.aDistrict = "";
      this.onAxisFilterChange();
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
      this.clearLayer("lightingLayer");
      this.clearLayer("signsLayer");

      const boundsLayers = [];

      if (this.showRoads && this.filteredRoadFeatures.length) {
        this.roadsLayer = L.geoJSON({ type: "FeatureCollection", features: this.filteredRoadFeatures }, {
          style: (f) => ({
            color: (f.properties && f.properties.color) || "#38bdf8",
            weight: 4,
            opacity: 0.92,
            lineCap: "round",
            lineJoin: "round",
          }),
          onEachFeature: (feature, layer) => {
            layer.bindPopup(axisPopupHtml(feature.properties || {}), { className: "axis-popup", maxWidth: 280 });
          },
        }).addTo(this.map);
        boundsLayers.push(this.roadsLayer);
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
      const layers = [this.roadsLayer, this.lightingLayer, this.signsLayer].filter(Boolean);
      if (!layers.length) return;
      try {
        const group = L.featureGroup(layers);
        this.map.fitBounds(group.getBounds(), { padding: [60, 70], maxZoom: 16, animate: false });
      } catch (e) {}
    },
  },
}).mount("#app");
