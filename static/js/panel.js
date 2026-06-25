/* ====== لوحة تحكم محور طريق محمد بن سلمان (Vue 3 + Leaflet + Django API) ====== */
const { createApp } = Vue;

const CENTER = [21.4275, 39.8235];
const ZOOM = 14;
const STATUS_COLORS = {
  critical: "rgb(220, 38, 38)",
  operational: "rgb(234, 88, 12)",
  maintenance: "rgb(217, 119, 6)",
  good: "rgb(22, 163, 74)",
};

function bridgeIcon(color, selected) {
  return L.divIcon({
    className: "",
    html: `<div class="bridge-marker ${selected ? "selected" : ""}" style="--bc:${color}">🌉</div>`,
    iconSize: [38, 38], iconAnchor: [19, 38],
  });
}

async function api(method, url, body, isForm) {
  const opt = { method, headers: {} };
  if (body && !isForm) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  if (body && isForm) opt.body = body;
  const res = await fetch(url, opt);
  if (!res.ok) throw new Error(await res.text());
  return res.status === 204 ? null : res.json();
}

createApp({
  data() {
    return {
      bridges: [], sel: null, draft: null,
      placingBridge: false, movingBridge: false,
      map: null, renderLayers: [],
      toastMsg: "", toastT: null,
    };
  },
  async mounted() {
    this.initMap();
    await this.load();
  },
  watch: {
    placingBridge(v) { this.updateCursor(); },
    movingBridge(v) { this.updateCursor(); },
  },
  methods: {
    statusColor(s) { return STATUS_COLORS[s] || "#3c7a5a"; },
    toast(m) { this.toastMsg = m; clearTimeout(this.toastT); this.toastT = setTimeout(() => this.toastMsg = "", 2600); },
    updateCursor() {
      const el = this.map && this.map.getContainer();
      if (el) el.style.cursor = (this.placingBridge || this.movingBridge) ? "crosshair" : "";
    },

    initMap() {
      this.map = L.map("admin-map").setView(CENTER, ZOOM);
      const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 19, attribution: "Esri" });
      const streets = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 20, attribution: "© CARTO" });
      satellite.addTo(this.map);
      L.control.layers({ "قمر صناعي": satellite, "خريطة شوارع": streets }, {}).addTo(this.map);
      this.map.on("click", e => this.onMapClick(e));
      setTimeout(() => this.map.invalidateSize(), 200);
      window.addEventListener("resize", () => this.map.invalidateSize());
    },

    async load(keepSelId) {
      this.bridges = await api("GET", "/api/bridges/");
      this.sel = keepSelId ? this.bridges.find(b => b.id === keepSelId) || null
        : (this.sel && this.bridges.find(b => b.id === this.sel.id)) || null;
      if (this.draft && this.draft.id && this.sel) {
        const d = this.sel.defects.find(x => x.id === this.draft.id);
        if (d) this.draft = this.toDraft(d);
      }
      this.render();
    },

    render() {
      this.renderLayers.forEach(l => this.map.removeLayer(l));
      this.renderLayers = [];
      this.bridges.forEach(b => {
        if (b.lat == null || b.lng == null) return;
        const isSel = this.sel && this.sel.id === b.id;
        const m = L.marker([b.lat, b.lng], { icon: bridgeIcon(b.color, isSel) }).addTo(this.map);
        m.on("click", () => { if (!this.placingBridge && !this.movingBridge) this.selectBridge(b.id); });
        this.renderLayers.push(m);
      });
    },

    onMapClick(e) {
      const ll = [e.latlng.lat, e.latlng.lng];
      if (this.placingBridge) { this.placingBridge = false; this.createBridge(ll); }
      else if (this.movingBridge && this.sel) { this.movingBridge = false; this.sel.lat = ll[0]; this.sel.lng = ll[1]; this.saveBridge(); this.toast("تم تحديث موقع الجسر ✓"); }
    },

    /* ----- الجسر ----- */
    startPlaceBridge() { this.placingBridge = true; this.movingBridge = false; this.toast("انقر على الخريطة لتحديد موقع الجسر"); },
    startMoveBridge() { if (!this.sel) return; this.movingBridge = true; this.placingBridge = false; this.toast("انقر على الخريطة لتحريك الجسر"); },
    async createBridge(ll) {
      try {
        const created = await api("POST", "/api/bridges/", { name: "جسر جديد", status: "operational", lat: ll[0], lng: ll[1] });
        await this.load(created.id); this.toast("تم إضافة الجسر ✓");
      } catch (e) { this.toast("خطأ في الإضافة"); console.error(e); }
    },
    selectBridge(id) {
      this.sel = this.bridges.find(b => b.id === id) || null;
      this.draft = null;
      this.render();
      if (this.sel) this.map.panTo([this.sel.lat, this.sel.lng]);
    },
    async saveBridge() {
      if (!this.sel) return;
      const b = this.sel;
      try {
        await api("PATCH", `/api/bridges/${b.id}/`, { name: b.name, status: b.status, lat: b.lat, lng: b.lng });
        await this.load(b.id); this.toast("تم الحفظ ✓");
      } catch (e) { this.toast("خطأ في الحفظ"); }
    },
    async deleteBridge(b) {
      if (!confirm("حذف هذا الجسر وكل الحالات المرتبطة؟")) return;
      await api("DELETE", `/api/bridges/${b.id}/`);
      if (this.sel && this.sel.id === b.id) { this.sel = null; this.draft = null; }
      await this.load(); this.toast("تم حذف الجسر");
    },

    /* ----- الحالات ----- */
    toDraft(d) {
      return { id: d.id, title: d.title, status: d.status, description: d.description,
        length_m: d.length_m, width_m: d.width_m, area_m2: d.area_m2, count: d.count,
        images: JSON.parse(JSON.stringify(d.images || [])) };
    },
    newDefect() {
      this.draft = { id: null, title: "", status: "open", description: "", length_m: 0, width_m: 0, area_m2: 0, count: 1, images: [] };
    },
    editDefect(d) { this.draft = this.toDraft(d); },
    async saveDefect() {
      if (!this.sel) return;
      const d = this.draft;
      const body = {
        bridge: this.sel.id, title: d.title || "حالة بدون اسم", status: d.status, description: d.description || "",
        length_m: d.length_m || 0, width_m: d.width_m || 0, area_m2: d.area_m2 || 0, count: d.count || 0,
      };
      try {
        let saved = d.id ? await api("PUT", `/api/defects/${d.id}/`, body) : await api("POST", "/api/defects/", body);
        await this.load(this.sel.id);
        const fresh = this.sel.defects.find(x => x.id === saved.id);
        this.draft = fresh ? this.toDraft(fresh) : null;
        this.toast("تم حفظ الحالة ✓ — يمكنك رفع الصور الآن");
      } catch (e) { this.toast("خطأ في حفظ الحالة"); console.error(e); }
    },
    cancelDefect() { this.draft = null; },
    async deleteDefect(d) {
      if (!confirm("حذف هذه الحالة؟")) return;
      await api("DELETE", `/api/defects/${d.id}/`);
      if (this.draft && this.draft.id === d.id) this.draft = null;
      await this.load(this.sel.id); this.toast("تم حذف الحالة");
    },

    /* ----- الصور ----- */
    async uploadImages(e) {
      if (!this.draft || !this.draft.id) return;
      const files = e.target.files; if (!files.length) return;
      const fd = new FormData();
      [...files].forEach(f => fd.append("image", f));
      try {
        await api("POST", `/api/defects/${this.draft.id}/upload/`, fd, true);
        await this.load(this.sel.id);
        const fresh = this.sel.defects.find(x => x.id === this.draft.id);
        if (fresh) this.draft = this.toDraft(fresh);
        this.toast("تم رفع الصور ✓");
      } catch (err) { this.toast("خطأ في رفع الصور"); console.error(err); }
      e.target.value = "";
    },
    async deleteImage(im) {
      await api("DELETE", `/api/images/${im.id}/`);
      await this.load(this.sel.id);
      const fresh = this.sel.defects.find(x => x.id === this.draft.id);
      if (fresh) this.draft = this.toDraft(fresh);
    },
  },
}).mount("#app");
