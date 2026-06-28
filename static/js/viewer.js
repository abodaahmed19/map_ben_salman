/* ====== عارض محور طريق محمد بن سلمان (Vue 3 + Leaflet + Chart.js) ====== */
const { createApp } = Vue;

const CENTER = [21.38866, 39.42683];
const ZOOM = 11;

const BRIDGE_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M2 18h20"/><path d="M3 18v-3a9 9 0 0 1 18 0v3"/><path d="M12 18v-6"/><path d="M7.5 18v-3.4"/><path d="M16.5 18v-3.4"/></svg>`;
const ROAD_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3 7 21"/><path d="M15 3l2 18"/><path d="M12 4.5v3"/><path d="M12 10.5v3"/><path d="M12 16.5v3"/></svg>`;

const ROAD_STATUS = { critical: "#dc2626", medium: "#ea580c", low: "#22c55e" };
const BRIDGE_STATUS = { critical: "#dc2626", operational: "#ea580c", maintenance: "#d97706", good: "#16a34a" };
const DEFECT_STATUS = { open: "#ea580c", in_progress: "#38bdf8", resolved: "#22c55e" };
const TREAT = { treated: "#16a34a", untreated: "#dc2626" };
const DIR = { mecca: "#a78bfa", jeddah: "#38bdf8" };
const PALETTE = ["#2563eb", "#dc2626", "#ea580c", "#16a34a", "#a78bfa", "#38bdf8", "#fb7185", "#34d399", "#fbbf24"];

function baseLayers() {
  // maxNativeZoom = أقصى مستوى فيه صور Esri فعلية للمنطقة؛ الأعلى يُكبَّر من نفس الصور
  // (يمنع بلاطة "Map data not yet available" ويمنع الأسود)
  const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 19, maxNativeZoom: 17, attribution: "Holy Makkah" });
  const streets = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19, maxNativeZoom: 19, attribution: "© OpenStreetMap, © Holy Makkah" });
  return { satellite, streets };
}
function bridgeIcon(color, selected) {
  return L.divIcon({ className: "", html: `<div class="bridge-marker ${selected ? "selected" : ""}" style="--bc:${color}">${BRIDGE_SVG}</div>`, iconSize: [40, 40], iconAnchor: [20, 40] });
}
function roadCaseIcon(color, selected) {
  return L.divIcon({ className: "", html: `<div class="road-marker ${selected ? "selected" : ""}" style="--bc:${color}">${ROAD_SVG}</div>`, iconSize: [38, 38], iconAnchor: [19, 38] });
}
function countBy(arr, fn) { const c = {}; arr.forEach(x => { const k = fn(x) || "—"; c[k] = (c[k] || 0) + 1; }); return c; }

createApp({
  data() {
    return {
      bridges: [], roadCases: [],
      selected: null, selectedType: null,
      lightbox: null, loading: true,
      map: null, cluster: null, markers: {}, slideTimer: null,
      filterType: "all",                       // "all" | "roads" | "bridges"
      fDirection: "", fTreatment: "", fStatus: "",
      fbTreatment: "", fbStatus: "",
      showDash: false,
    };
  },
  computed: {
    currentImage() { return this.lightbox && this.lightbox.defect.images[this.lightbox.index]; },
    gmapsUrl() { return this.selected ? `https://www.google.com/maps/search/?api=1&query=${this.selected.lat},${this.selected.lng}` : "#"; },
    visibleBridges() { return this.filterType === "roads" ? [] : this.bridges.filter(b => this.bridgeMatches(b)); },
    visibleRoadCases() { return this.filterType === "bridges" ? [] : this.roadCases.filter(c => this.caseMatches(c)); },
    visibleCount() { return this.visibleBridges.length + this.visibleRoadCases.length; },
    dashMode() { return this.filterType === "bridges" ? "bridges" : "roads"; },
  },
  watch: {
    filterType() { this.applyFilter(); },
    fDirection() { this.applyFilter(); }, fTreatment() { this.applyFilter(); }, fStatus() { this.applyFilter(); },
    fbTreatment() { this.applyFilter(); }, fbStatus() { this.applyFilter(); },
  },
  async mounted() {
    this.initMap();
    await this.load();
    window.addEventListener("keydown", e => {
      if (e.key !== "Escape") return;
      if (this.lightbox) this.closeLightbox();
      else if (this.showDash) this.closeDash();
      else if (this.selected) this.closePanel();
    });
  },
  methods: {
    initMap() {
      this.map = L.map("map", { zoomControl: false, maxZoom: 19 }).setView(CENTER, ZOOM);
      L.control.zoom({ position: "topleft" }).addTo(this.map);
      const { satellite, streets } = baseLayers();
      satellite.addTo(this.map);
      L.control.layers({ "قمر صناعي": satellite, "خريطة شوارع": streets }, {}, { position: "topleft" }).addTo(this.map);
      // تجميع الماركرات: يظهر عدد العناصر في المنطقة، والضغط يقرّب
      this.cluster = L.markerClusterGroup({
        maxClusterRadius: 52, showCoverageOnHover: false, spiderfyOnMaxZoom: true,
        animate: false,                  // بدون أنيميشن وقت الزووم → النقاط تظهر في مكانها الصح فورًا
        animateAddingMarkers: false,
        iconCreateFunction(c) {
          const n = c.getChildCount();
          const size = n < 10 ? 40 : n < 50 ? 48 : 56;
          return L.divIcon({ className: "", html: `<div class="cluster-marker" style="width:${size}px;height:${size}px">${n}</div>`, iconSize: [size, size] });
        },
      }).addTo(this.map);
    },
    async load() {
      try {
        const [bridgesRes, roadsRes] = await Promise.all([fetch("/api/bridges/"), fetch("/api/roads/")]);
        this.bridges = await bridgesRes.json();
        const roads = await roadsRes.json();
        this.roadCases = [];
        roads.forEach(r => (r.defects || []).forEach(d => {
          this.roadCases.push({ ...d, road_segment: r.segment, road_direction: r.direction, direction_display: r.direction_display });
        }));
        this.render();
      } finally { this.loading = false; }
    },
    render() {
      this.bridges.forEach(b => {
        if (b.lat == null || b.lng == null) return;
        const m = L.marker([b.lat, b.lng], { icon: bridgeIcon(b.color, false) });
        m.on("click", () => this.openItem(b.id, "bridge"));
        this.markers[`bridge-${b.id}`] = { marker: m, type: "bridge", data: b };
      });
      this.roadCases.forEach(d => {
        if (d.lat == null || d.lng == null) return;
        const m = L.marker([d.lat, d.lng], { icon: roadCaseIcon(d.color, false) });
        m.on("click", () => this.openItem(d.id, "roadcase"));
        this.markers[`case-${d.id}`] = { marker: m, type: "roadcase", data: d };
      });
      this.applyFilter();
      setTimeout(() => this.map.invalidateSize(), 200);
      window.addEventListener("resize", () => this.map.invalidateSize());
    },
    bridgeMatches(b) {
      if (this.fbStatus && b.status !== this.fbStatus) return false;
      if (this.fbTreatment && !(b.defects || []).some(d => d.status === this.fbTreatment)) return false;
      return true;
    },
    caseMatches(d) {
      if (this.fStatus && d.status !== this.fStatus) return false;
      if (this.fTreatment && d.treatment_type !== this.fTreatment) return false;
      if (this.fDirection && d.road_direction !== this.fDirection) return false;
      return true;
    },
    matches(type, data) {
      if (this.filterType === "roads") return type === "roadcase" && this.caseMatches(data);
      if (this.filterType === "bridges") return type === "bridge" && this.bridgeMatches(data);
      return type === "bridge" ? this.bridgeMatches(data) : this.caseMatches(data);
    },
    applyFilter(fit = true) {
      const bounds = [], show = [];
      Object.values(this.markers).forEach(({ marker, type, data }) => {
        if (this.matches(type, data)) { show.push(marker); bounds.push(marker.getLatLng()); }
        else if (this.selected && this.selectedType === type && this.selected.id === data.id) this.closePanel();
      });
      this.cluster.clearLayers();
      this.cluster.addLayers(show);
      if (fit && bounds.length) this.map.fitBounds(bounds, { padding: [80, 90], maxZoom: ZOOM });
    },
    zoomToVisible() {
      const bounds = [];
      Object.values(this.markers).forEach(({ marker, type, data }) => { if (this.matches(type, data)) bounds.push(marker.getLatLng()); });
      if (bounds.length) this.map.fitBounds(bounds, { padding: [60, 70], maxZoom: 17 });
    },
    iconFor(type, data, selected) { return type === "bridge" ? bridgeIcon(data.color, selected) : roadCaseIcon(data.color, selected); },
    openItem(id, type) {
      this.selected = (type === "bridge" ? this.bridges : this.roadCases).find(x => x.id === id) || null;
      this.selectedType = type;
      Object.values(this.markers).forEach(({ marker, type: mt, data }) => marker.setIcon(this.iconFor(mt, data, mt === type && data.id === id)));
      if (this.selected) this.map.panTo([this.selected.lat, this.selected.lng]);
    },
    closePanel() {
      this.selected = null; this.selectedType = null;
      Object.values(this.markers).forEach(({ marker, type, data }) => marker.setIcon(this.iconFor(type, data, false)));
    },
    /* ---------- لوحة البيانات ---------- */
    openDash() { this.showDash = true; this.$nextTick(() => this.buildCharts()); },
    closeDash() { this.showDash = false; this.destroyCharts(); },
    destroyCharts() { (this._charts || []).forEach(c => { try { c.destroy(); } catch (e) {} }); this._charts = []; },
    focusFromDash(item, type) { this.closeDash(); this.openItem(item.id, type); this.map.setView([item.lat, item.lng], 17); },
    doughnut(id, labels, data, colors) {
      const el = document.getElementById(id); if (!el) return;
      this._charts.push(new Chart(el.getContext("2d"), {
        type: "doughnut",
        data: { labels, datasets: [{ data, backgroundColor: colors, borderColor: "#0e1c18", borderWidth: 2 }] },
        options: { maintainAspectRatio: false, responsive: true, plugins: { legend: { position: "bottom", labels: { color: "#cfe0d9", font: { family: "Tajawal" } } } } },
      }));
    },
    bar(id, labels, data, color) {
      const el = document.getElementById(id); if (!el) return;
      this._charts.push(new Chart(el.getContext("2d"), {
        type: "bar",
        data: { labels, datasets: [{ data, backgroundColor: color, borderRadius: 5 }] },
        options: { maintainAspectRatio: false, responsive: true, plugins: { legend: { display: false } },
          scales: { x: { grid: { display: false }, ticks: { color: "#9fb1aa" } }, y: { grid: { color: "rgba(136,192,176,.12)" }, ticks: { color: "#9fb1aa", precision: 0 } } } },
      }));
    },
    buildCharts() {
      this.destroyCharts(); this._charts = [];
      if (typeof Chart === "undefined") return;
      Chart.defaults.font.family = "Tajawal, sans-serif";
      if (this.dashMode === "bridges") {
        const v = this.visibleBridges;
        const bs = countBy(v, b => b.status_display);
        this.doughnut("ch1", Object.keys(bs), Object.values(bs), Object.keys(bs).map((k, i) => PALETTE[i % PALETTE.length]));
        const defs = v.flatMap(b => b.defects || []);
        const ds = countBy(defs, d => d.status_display);
        this.bar("ch2", Object.keys(ds), Object.values(ds), "#38bdf8");
      } else {
        const v = this.visibleRoadCases;
        const st = countBy(v, d => d.status_display);
        this.doughnut("ch1", Object.keys(st), Object.values(st), Object.keys(st).map(k => (k === "حرج" ? ROAD_STATUS.critical : k === "متوسط" ? ROAD_STATUS.medium : ROAD_STATUS.low)));
        const tr = countBy(v, d => d.treatment_type_display);
        this.doughnut("ch2", Object.keys(tr), Object.values(tr), Object.keys(tr).map(k => (k === "معالج" ? TREAT.treated : TREAT.untreated)));
        const di = countBy(v, d => d.direction_display);
        this.doughnut("ch3", Object.keys(di), Object.values(di), Object.keys(di).map(k => (k === "جدة" ? DIR.jeddah : DIR.mecca)));
        const sg = countBy(v, d => d.road_segment);
        const sk = Object.keys(sg).sort();
        this.bar("ch4", sk, sk.map(k => sg[k]), "#a78bfa");
      }
    },
    /* ---------- معرض الصور ---------- */
    openImages(defect, index = 0) {
      if (!defect || !defect.images || !defect.images.length) return;
      this.lightbox = { defect, index: index || 0 }; this.startAutoSlide();
    },
    prevImage() { if (!this.lightbox) return; const c = this.lightbox.defect.images.length; this.lightbox.index = (this.lightbox.index + c - 1) % c; this.resetAutoSlide(); },
    nextImage() { if (!this.lightbox) return; const c = this.lightbox.defect.images.length; this.lightbox.index = (this.lightbox.index + 1) % c; this.resetAutoSlide(); },
    startAutoSlide() { this.clearAutoSlide(); if (!this.lightbox || this.lightbox.defect.images.length < 2) return; this.slideTimer = setInterval(() => { if (!this.lightbox) return; const c = this.lightbox.defect.images.length; this.lightbox.index = (this.lightbox.index + 1) % c; }, 2800); },
    resetAutoSlide() { this.startAutoSlide(); },
    clearAutoSlide() { if (this.slideTimer) { clearInterval(this.slideTimer); this.slideTimer = null; } },
    closeLightbox() { this.clearAutoSlide(); this.lightbox = null; },
  },
}).mount("#app");
