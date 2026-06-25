/* ====== عارض محور طريق محمد بن سلمان (Vue 3) ====== */
const { createApp } = Vue;

const CENTER = [21.4275, 39.8235];
const ZOOM = 14;

function baseLayers() {
  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "Esri" });
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

createApp({
  data() {
    return { bridges: [], selected: null, lightbox: null, loading: true,
             map: null, markers: {}, slideTimer: null };
  },
  computed: {
    openCount() { return this.bridges.reduce((s, b) => s + b.open_count, 0); },
    critCount() { return this.bridges.filter(b => b.status === "critical").length; },
    currentImage() {
      return this.lightbox && this.lightbox.defect.images[this.lightbox.index];
    },
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
        const res = await fetch("/api/bridges/");
        this.bridges = await res.json();
        this.render();
      } finally { this.loading = false; }
    },
    render() {
      const bounds = [];
      this.bridges.forEach(b => {
        if (b.lat == null || b.lng == null) return;
        const m = L.marker([b.lat, b.lng], { icon: bridgeIcon(b.color, false) }).addTo(this.map);
        m.on("click", () => this.openBridge(b.id));
        this.markers[b.id] = m;
        bounds.push([b.lat, b.lng]);
      });
      if (bounds.length) this.map.fitBounds(bounds, { padding: [80, 90], maxZoom: 20 });
      setTimeout(() => this.map.invalidateSize(), 200);
      window.addEventListener("resize", () => this.map.invalidateSize());
    },
    openBridge(id) {
      this.selected = this.bridges.find(b => b.id === id) || null;
      Object.entries(this.markers).forEach(([bid, m]) => {
        const b = this.bridges.find(x => x.id === +bid);
        m.setIcon(bridgeIcon(b.color, +bid === id));
      });
      if (this.selected) this.map.panTo([this.selected.lat, this.selected.lng]);
    },
    closePanel() {
      this.selected = null;
      Object.entries(this.markers).forEach(([bid, m]) => {
        const b = this.bridges.find(x => x.id === +bid);
        m.setIcon(bridgeIcon(b.color, false));
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
