/* ====== عارض محور طريق محمد بن سلمان (Vue 3) ====== */
const { createApp } = Vue;

const CENTER = [21.38866 , 39.42683];
const ZOOM = 11;

function baseLayers() {
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "Holy Makkah" });
  const streets = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    { maxZoom: 20, attribution: "© OpenStreetMap, © CARTO" });
  return { satellite, streets };
}

function bridgeIcon(color, selected) {
  return L.divIcon({
    className: "",
    html: `<div class="bridge-marker ${selected ? "selected" : ""}" style="--bc:${color}">🌉</div>`,
    iconSize: [38, 38], iconAnchor: [19, 38],
  });
}

function roadIcon(color, selected) {
  return L.divIcon({
    className: "",
    html: `<div class="road-marker ${selected ? "selected" : ""}" style="--bc:${color}">🛣️</div>`,
    iconSize: [38, 38], iconAnchor: [19, 38],
  });
}

createApp({
  data() {
    return { 
      bridges: [], 
      roads: [],
      selected: null, 
      lightbox: null, 
      loading: true,
      map: null, 
      markers: {}, 
      slideTimer: null,
      showBridges: true,
      showRoads: true
    };
  },
  computed: {
    openCount() { return this.bridges.reduce((s, b) => s + b.open_count, 0); },
    critCount() { return this.bridges.filter(b => b.status === "critical").length; },
    currentImage() {
      return this.lightbox && this.lightbox.defect.images[this.lightbox.index];
    },
  },
  watch: {
    showBridges() { this.updateMarkers(); },
    showRoads() { this.updateMarkers(); },
  },
  async mounted() {
    this.initMap();
    await this.load();
    window.addEventListener("keydown", e => {
      if (e.key !== "Escape") return;
      if (this.lightbox) this.closeLightbox();
      else if (this.selected) this.closePanel();
    });
  },
  methods: {
    initMap() {
      this.map = L.map("map", { zoomControl: false, maxZoom: 20 }).setView(CENTER, ZOOM);
      L.control.zoom({ position: "topleft" }).addTo(this.map);
      const { satellite, streets } = baseLayers();
      satellite.addTo(this.map);
      L.control.layers({ "قمر صناعي": satellite, "خريطة شوارع": streets }, {}, { position: "topleft" }).addTo(this.map);
    },
    async load() {
      try {
        const [bridgesRes, roadsRes] = await Promise.all([
          fetch("/api/bridges/"),
          fetch("/api/roads/")
        ]);
        this.bridges = await bridgesRes.json();
        this.roads = await roadsRes.json();
        this.render();
      } finally { this.loading = false; }
    },
    render() {
      const bounds = [];
      
      // Render bridges
      this.bridges.forEach(b => {
        if (b.lat == null || b.lng == null) return;
        const m = L.marker([b.lat, b.lng], { icon: bridgeIcon(b.color, false) }).addTo(this.map);
        m.on("click", () => this.openBridge(b.id, "bridge"));
        this.markers[`bridge-${b.id}`] = { marker: m, type: "bridge", data: b };
        bounds.push([b.lat, b.lng]);
      });

      // Render roads
      this.roads.forEach(r => {
        if (r.lat == null || r.lng == null) return;
        const m = L.marker([r.lat, r.lng], { icon: roadIcon(r.color, false) }).addTo(this.map);
        m.on("click", () => this.openBridge(r.id, "road"));
        this.markers[`road-${r.id}`] = { marker: m, type: "road", data: r };
        bounds.push([r.lat, r.lng]);
      });

      if (bounds.length) this.map.fitBounds(bounds, { padding: [80, 90], maxZoom: ZOOM });
      setTimeout(() => this.map.invalidateSize(), 200);
      window.addEventListener("resize", () => this.map.invalidateSize());
    },
    updateMarkers() {
      Object.entries(this.markers).forEach(([key, { marker, type, data }]) => {
        const shouldShow = (type === "bridge" && this.showBridges) || (type === "road" && this.showRoads);
        if (shouldShow) {
          marker.addTo(this.map);
        } else {
          this.map.removeLayer(marker);
          if (this.selected && this.selected.id === data.id) {
            this.closePanel();
          }
        }
      });
    },
    openBridge(id, type) {
      if (type === "bridge") {
        this.selected = this.bridges.find(b => b.id === id) || null;
      } else {
        this.selected = this.roads.find(r => r.id === id) || null;
      }

      Object.entries(this.markers).forEach(([key, { marker, type: mtype, data }]) => {
        const isSelected = mtype === type && data.id === id;
        if (mtype === "bridge") {
          const b = this.bridges.find(x => x.id === data.id);
          marker.setIcon(bridgeIcon(b.color, isSelected));
        } else {
          const r = this.roads.find(x => x.id === data.id);
          marker.setIcon(roadIcon(r.color, isSelected));
        }
      });

      if (this.selected) this.map.panTo([this.selected.lat, this.selected.lng]);
    },
    closePanel() {
      this.selected = null;
      Object.entries(this.markers).forEach(([key, { marker, type, data }]) => {
        if (type === "bridge") {
          const b = this.bridges.find(x => x.id === data.id);
          marker.setIcon(bridgeIcon(b.color, false));
        } else {
          const r = this.roads.find(x => x.id === data.id);
          marker.setIcon(roadIcon(r.color, false));
        }
      });
    },
    openImages(defect, index = 0) {
      if (!defect || !defect.images || !defect.images.length) return;
      this.lightbox = { defect, index: index || 0 };
      this.startAutoSlide();
    },
    prevImage() {
      if (!this.lightbox) return;
      const count = this.lightbox.defect.images.length;
      this.lightbox.index = (this.lightbox.index + count - 1) % count;
      this.resetAutoSlide();
    },
    nextImage() {
      if (!this.lightbox) return;
      const count = this.lightbox.defect.images.length;
      this.lightbox.index = (this.lightbox.index + 1) % count;
      this.resetAutoSlide();
    },
    startAutoSlide() {
      this.clearAutoSlide();
      if (!this.lightbox || this.lightbox.defect.images.length < 2) return;
      this.slideTimer = setInterval(() => {
        if (!this.lightbox) return;
        const count = this.lightbox.defect.images.length;
        this.lightbox.index = (this.lightbox.index + 1) % count;
      }, 2800);
    },
    resetAutoSlide() {
      this.startAutoSlide();
    },
    clearAutoSlide() {
      if (this.slideTimer) { clearInterval(this.slideTimer); this.slideTimer = null; }
    },
    closeLightbox() {
      this.clearAutoSlide();
      this.lightbox = null;
    },

  },
}).mount("#app");
