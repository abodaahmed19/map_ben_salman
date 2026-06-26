/* ====== لوحة تحكم محور طريق محمد بن سلمان (Vue 3 + Leaflet + Django API) ====== */
const { createApp } = Vue;

const CENTER = [21.38866, 39.42683];
const ZOOM = 14;
const STATUS_COLORS = {
  critical: "rgb(220, 38, 38)",
  operational: "rgb(234, 88, 12)",
  maintenance: "rgb(217, 119, 6)",
  good: "rgb(22, 163, 74)",
};

const ROAD_STATUS_COLORS = {
  critical: "rgb(220, 38, 38)",
  medium: "rgb(234, 88, 12)",
  low: "rgb(34, 197, 94)",
};

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
      activeTab: "bridges", // "bridges" | "roads"
      bridges: [], selBridge: null, draft: null,
      placingBridge: false, movingBridge: false,
      roads: [], selRoad: null, roadDraft: null,
      placingRoad: false, movingRoad: false,
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
    placingRoad(v) { this.updateCursor(); },
    movingRoad(v) { this.updateCursor(); },
    activeTab() {
      // Clear selections when switching tabs
      if (this.activeTab === "bridges") {
        this.selRoad = null;
        this.roadDraft = null;
        this.placingRoad = false;
        this.movingRoad = false;
      } else {
        this.selBridge = null;
        this.draft = null;
        this.placingBridge = false;
        this.movingBridge = false;
      }
      this.render();
    }
  },
  methods: {
    setTab(tab) { this.activeTab = tab; },
    statusColor(s) { return STATUS_COLORS[s] || "#3c7a5a"; },
    roadStatusColor(s) { return ROAD_STATUS_COLORS[s] || "#3c7a5a"; },
    toast(m) { this.toastMsg = m; clearTimeout(this.toastT); this.toastT = setTimeout(() => this.toastMsg = "", 2600); },
    updateCursor() {
      const el = this.map && this.map.getContainer();
      if (el) el.style.cursor = (this.placingBridge || this.movingBridge || this.placingRoad || this.movingRoad) ? "crosshair" : "";
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
      this.roads = await api("GET", "/api/roads/");
      
      this.selBridge = keepSelId && this.activeTab === 'bridges' ? this.bridges.find(b => b.id === keepSelId) || null
        : (this.selBridge && this.bridges.find(b => b.id === this.selBridge.id)) || null;
      if (this.draft && this.draft.id && this.selBridge) {
        const d = this.selBridge.defects.find(x => x.id === this.draft.id);
        if (d) this.draft = this.toDraft(d);
      }

      this.selRoad = keepSelId && this.activeTab === 'roads' ? this.roads.find(r => r.id === keepSelId) || null
        : (this.selRoad && this.roads.find(r => r.id === this.selRoad.id)) || null;
      if (this.roadDraft && this.roadDraft.id && this.selRoad) {
        const d = this.selRoad.defects.find(x => x.id === this.roadDraft.id);
        if (d) this.roadDraft = this.toRoadDraft(d);
      }

      this.render();
    },

    render() {
      this.renderLayers.forEach(l => this.map.removeLayer(l));
      this.renderLayers = [];
      
      if (this.activeTab === 'bridges') {
        this.bridges.forEach(b => {
          if (b.lat == null || b.lng == null) return;
          const isSel = this.selBridge && this.selBridge.id === b.id;
          const m = L.marker([b.lat, b.lng], { icon: bridgeIcon(b.color, isSel) }).addTo(this.map);
          m.on("click", () => { if (!this.placingBridge && !this.movingBridge) this.selectBridge(b.id); });
          this.renderLayers.push(m);
        });
      } else if (this.activeTab === 'roads') {
        this.roads.forEach(r => {
          if (r.lat == null || r.lng == null) return;
          const isSel = this.selRoad && this.selRoad.id === r.id;
          const m = L.marker([r.lat, r.lng], { icon: roadIcon(r.color, isSel) }).addTo(this.map);
          m.on("click", () => { if (!this.placingRoad && !this.movingRoad) this.selectRoad(r.id); });
          this.renderLayers.push(m);
        });
      }
    },

    onMapClick(e) {
      const ll = [e.latlng.lat, e.latlng.lng];
      if (this.placingBridge) { this.placingBridge = false; this.createBridge(ll); }
      else if (this.movingBridge && this.selBridge) { this.movingBridge = false; this.selBridge.lat = ll[0]; this.selBridge.lng = ll[1]; this.saveBridge(); this.toast("تم تحديث موقع الجسر ✓"); }
      else if (this.placingRoad) { this.placingRoad = false; this.createRoad(ll); }
      else if (this.movingRoad && this.selRoad) { this.movingRoad = false; this.selRoad.lat = ll[0]; this.selRoad.lng = ll[1]; this.saveRoad(); this.toast("تم تحديث موقع الطريق ✓"); }
    },

    /* ----- الجسر ----- */
    startPlaceBridge() { this.placingBridge = true; this.movingBridge = false; this.toast("انقر على الخريطة لتحديد موقع الجسر"); },
    startMoveBridge() { if (!this.selBridge) return; this.movingBridge = true; this.placingBridge = false; this.toast("انقر على الخريطة لتحريك الجسر"); },
    async createBridge(ll) {
      try {
        const created = await api("POST", "/api/bridges/", { name: "جسر جديد", status: "operational", lat: ll[0], lng: ll[1] });
        await this.load(created.id); this.toast("تم إضافة الجسر ✓");
      } catch (e) { this.toast("خطأ في الإضافة"); console.error(e); }
    },
    selectBridge(id) {
      this.selBridge = this.bridges.find(b => b.id === id) || null;
      this.draft = null;
      this.render();
      if (this.selBridge) this.map.panTo([this.selBridge.lat, this.selBridge.lng]);
    },
    async saveBridge() {
      if (!this.selBridge) return;
      const b = this.selBridge;
      try {
        await api("PATCH", `/api/bridges/${b.id}/`, { name: b.name, description: b.description || "", status: b.status, lat: b.lat, lng: b.lng });
        await this.load(b.id); this.toast("تم الحفظ ✓");
      } catch (e) { this.toast("خطأ في الحفظ"); }
    },
    async deleteBridge(b) {
      if (!confirm("حذف هذا الجسر وكل الحالات المرتبطة؟")) return;
      await api("DELETE", `/api/bridges/${b.id}/`);
      if (this.selBridge && this.selBridge.id === b.id) { this.selBridge = null; this.draft = null; }
      await this.load(); this.toast("تم حذف الجسر");
    },

    /* ----- الطرق ----- */
    startPlaceRoad() { this.placingRoad = true; this.movingRoad = false; this.toast("انقر على الخريطة لتحديد موقع الطريق"); },
    startMoveRoad() { if (!this.selRoad) return; this.movingRoad = true; this.placingRoad = false; this.toast("انقر على الخريطة لتحريك الطريق"); },
    async createRoad(ll) {
      try {
        const created = await api("POST", "/api/roads/", { segment: "مقطع جديد", status: "medium", lat: ll[0], lng: ll[1] });
        await this.load(created.id); this.toast("تم إضافة الطريق ✓");
      } catch (e) { this.toast("خطأ في الإضافة"); console.error(e); }
    },
    selectRoad(id) {
      this.selRoad = this.roads.find(r => r.id === id) || null;
      this.render();
      if (this.selRoad) this.map.panTo([this.selRoad.lat, this.selRoad.lng]);
    },
    async saveRoad() {
      if (!this.selRoad) return;
      const r = this.selRoad;
      try {
        await api("PATCH", `/api/roads/${r.id}/`, { segment: r.segment, status: r.status, lat: r.lat, lng: r.lng });
        await this.load(r.id); this.toast("تم الحفظ ✓");
      } catch (e) { this.toast("خطأ في الحفظ"); }
    },
    async deleteRoad(r) {
      if (!confirm("حذف هذا الطريق بالكامل؟")) return;
      await api("DELETE", `/api/roads/${r.id}/`);
      if (this.selRoad && this.selRoad.id === r.id) { this.selRoad = null; }
      await this.load(); this.toast("تم حذف الطريق");
    },

    /* ----- الحالات (للجسور فقط) ----- */
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
      if (!this.selBridge) return;
      const d = this.draft;
      const body = {
        bridge: this.selBridge.id, title: d.title || "حالة بدون اسم", status: d.status, description: d.description || "",
        length_m: d.length_m || 0, width_m: d.width_m || 0, area_m2: d.area_m2 || 0, count: d.count || 0,
      };
      try {
        let saved = d.id ? await api("PUT", `/api/defects/${d.id}/`, body) : await api("POST", "/api/defects/", body);
        await this.load(this.selBridge.id);
        const fresh = this.selBridge.defects.find(x => x.id === saved.id);
        this.draft = fresh ? this.toDraft(fresh) : null;
        this.toast("تم حفظ الحالة ✓ — يمكنك رفع الصور الآن");
      } catch (e) { this.toast("خطأ في حفظ الحالة"); console.error(e); }
    },
    cancelDefect() { this.draft = null; },
    async deleteDefect(d) {
      if (!confirm("حذف هذه الحالة؟")) return;
      await api("DELETE", `/api/defects/${d.id}/`);
      if (this.draft && this.draft.id === d.id) this.draft = null;
      await this.load(this.selBridge.id); this.toast("تم حذف الحالة");
    },

    /* ----- الصور ----- */
    async uploadImages(e) {
      if (!this.draft || !this.draft.id) return;
      const files = e.target.files; if (!files.length) return;
      const fd = new FormData();
      [...files].forEach(f => fd.append("image", f));
      try {
        await api("POST", `/api/defects/${this.draft.id}/upload/`, fd, true);
        await this.load(this.selBridge.id);
        const fresh = this.selBridge.defects.find(x => x.id === this.draft.id);
        if (fresh) this.draft = this.toDraft(fresh);
        this.toast("تم رفع الصور ✓");
      } catch (err) { this.toast("خطأ في رفع الصور"); console.error(err); }
      e.target.value = "";
    },
    async deleteImage(im) {
      await api("DELETE", `/api/images/${im.id}/`);
      await this.load(this.selBridge.id);
      const fresh = this.selBridge.defects.find(x => x.id === this.draft.id);
      if (fresh) this.draft = this.toDraft(fresh);
    },

    /* ----- حالات الطرق ----- */
    toRoadDraft(d) {
      return { id: d.id, title: d.title, status: d.status, direction: d.direction, observation: d.observation, description: d.description, treatment_type: d.treatment_type,
        images: JSON.parse(JSON.stringify(d.images || [])) };
    },
    newRoadDefect() {
      this.roadDraft = { id: null, title: "", status: "medium", direction: "mecca", observation: "", description: "", treatment_type: "", images: [] };
    },
    editRoadDefect(d) { this.roadDraft = this.toRoadDraft(d); },
    async saveRoadDefect() {
      if (!this.selRoad) return;
      const d = this.roadDraft;
      const body = {
        road: this.selRoad.id, title: d.title || "", status: d.status, direction: d.direction,
        observation: d.observation || "", description: d.description || "", treatment_type: d.treatment_type || ""
      };
      try {
        let saved = d.id ? await api("PUT", `/api/road-defects/${d.id}/`, body) : await api("POST", "/api/road-defects/", body);
        await this.load(this.selRoad.id);
        const fresh = this.selRoad.defects.find(x => x.id === saved.id);
        this.roadDraft = fresh ? this.toRoadDraft(fresh) : null;
        this.toast("تم حفظ الحالة ✓ — يمكنك رفع الصور الآن");
      } catch (e) { this.toast("خطأ في حفظ الحالة"); console.error(e); }
    },
    cancelRoadDefect() { this.roadDraft = null; },
    async deleteRoadDefect(d) {
      if (!confirm("حذف هذه الحالة؟")) return;
      await api("DELETE", `/api/road-defects/${d.id}/`);
      if (this.roadDraft && this.roadDraft.id === d.id) this.roadDraft = null;
      await this.load(this.selRoad.id); this.toast("تم حذف الحالة");
    },
    async uploadRoadImages(e) {
      if (!this.roadDraft || !this.roadDraft.id) return;
      const files = e.target.files; if (!files.length) return;
      const fd = new FormData();
      [...files].forEach(f => fd.append("image", f));
      try {
        await api("POST", `/api/road-defects/${this.roadDraft.id}/upload/`, fd, true);
        await this.load(this.selRoad.id);
        const fresh = this.selRoad.defects.find(x => x.id === this.roadDraft.id);
        if (fresh) this.roadDraft = this.toRoadDraft(fresh);
        this.toast("تم رفع الصور ✓");
      } catch (err) { this.toast("خطأ في رفع الصور"); console.error(err); }
      e.target.value = "";
    },
    async deleteRoadImage(im) {
      await api("DELETE", `/api/road-images/${im.id}/`);
      await this.load(this.selRoad.id);
      const fresh = this.selRoad.defects.find(x => x.id === this.roadDraft.id);
      if (fresh) this.roadDraft = this.toRoadDraft(fresh);
    },
  },
}).mount("#app");
