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
  return `<div class="axis-popup-title">${p.street || p.name || "مقطع"}</div>
    ${row("رمز المقطع", p.segment_code)}
    ${row("البلدية", p.municipality)}
    ${row("الحي", p.district)}
    ${row("الحي الفرعي", p.sub_district)}
    ${row("الاتجاه", p.direction_label || p.direction)}
    ${row("من", p.from_street)}
    ${row("إلى", p.to_street)}
    ${row("الطول", p.length_m ? `${Number(p.length_m).toFixed(1)} م` : "")}
    ${row("العرض", p.width_m ? `${p.width_m} م` : "")}`;
}

createApp({
  data() {
    return {
      loading: true,
      filterOpen: true,
      map: null,
      axisFeatures: [],
      axisLayer: null,
      aStreet: "", aMunicipality: "", aDistrict: "", aDirection: "",
    };
  },
  computed: {
    filteredAxisFeatures() {
      return this.axisFeatures.filter(f => this.axisFeatureMatches(f.properties || {}));
    },
    visibleAxisCount() { return this.filteredAxisFeatures.length; },
    axisMunicipalities() {
      const set = new Set();
      this.axisFeatures.forEach(f => {
        const p = f.properties || {};
        if (this.aStreet && p.street !== this.aStreet) return;
        if (p.municipality) set.add(p.municipality);
      });
      return [...set].sort();
    },
    axisDistricts() {
      const set = new Set();
      this.axisFeatures.forEach(f => {
        const p = f.properties || {};
        if (this.aStreet && p.street !== this.aStreet) return;
        if (this.aMunicipality && p.municipality !== this.aMunicipality) return;
        if (p.district) set.add(p.district);
      });
      return [...set].sort();
    },
  },
  watch: {
    aStreet() { this.onAxisFilterChange(); },
    aMunicipality() { this.onAxisMunicipalityChange(); },
    aDistrict() { this.onAxisFilterChange(); },
    aDirection() { this.onAxisFilterChange(); },
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
        const res = await fetch("/static/data/axis-assets.geojson");
        const data = await res.json();
        this.axisFeatures = data.features || [];
        this.renderAxisLayer(true);
      } catch (e) {
        console.error("axis assets load failed", e);
      } finally {
        this.loading = false;
      }
    },
    axisFeatureMatches(p) {
      if (this.aStreet && p.street !== this.aStreet) return false;
      if (this.aMunicipality && p.municipality !== this.aMunicipality) return false;
      if (this.aDistrict && p.district !== this.aDistrict) return false;
      if (this.aDirection && p.direction !== this.aDirection) return false;
      return true;
    },
    onAxisMunicipalityChange() {
      if (this.aDistrict && !this.axisDistricts.includes(this.aDistrict)) this.aDistrict = "";
      this.onAxisFilterChange();
    },
    onAxisFilterChange() {
      this.renderAxisLayer(false);
    },
    resetAxisFilters() {
      this.aStreet = "";
      this.aMunicipality = "";
      this.aDistrict = "";
      this.aDirection = "";
      this.onAxisFilterChange();
    },
    clearAxisLayer() {
      if (this.axisLayer) {
        this.map.removeLayer(this.axisLayer);
        this.axisLayer = null;
      }
    },
    renderAxisLayer(fit = false) {
      if (!this.map) return;
      this.clearAxisLayer();
      const features = this.filteredAxisFeatures;
      if (!features.length) return;
      this.axisLayer = L.geoJSON({ type: "FeatureCollection", features }, {
        style: (f) => ({
          color: (f.properties && f.properties.color) || "#fbbf24",
          weight: 4,
          opacity: 0.92,
          lineCap: "round",
          lineJoin: "round",
        }),
        onEachFeature: (feature, layer) => {
          const p = feature.properties || {};
          layer.bindPopup(axisPopupHtml(p), { className: "axis-popup", maxWidth: 280 });
        },
      }).addTo(this.map);
      if (fit) {
        try { this.map.fitBounds(this.axisLayer.getBounds(), { padding: [60, 70], maxZoom: 14, animate: false }); } catch (e) {}
      }
    },
    zoomToAxis() {
      if (this.axisLayer) {
        try { this.map.fitBounds(this.axisLayer.getBounds(), { padding: [60, 70], maxZoom: 16, animate: false }); } catch (e) {}
      }
    },
  },
}).mount("#app");
