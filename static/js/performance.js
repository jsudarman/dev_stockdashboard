"use strict";

let data = {};
let sortMode = "today";

const grid = document.getElementById("grid");
const loader = document.getElementById("loader");
const dateLabel = document.getElementById("date-label");
const heatStrip = document.getElementById("heat-strip");
const mockBadge = document.getElementById("mock-badge");
const overlay = document.getElementById("detail-overlay");
const detailContent = document.getElementById("detail-content");

function fmt(v, d = 2) {
  return v == null ? "—" : Number(v).toFixed(d);
}

function fmtPct(v, d = 2) {
  if (v == null) return "—";
  return (v >= 0 ? "+" : "") + Number(v).toFixed(d) + "%";
}

function pctCls(v) {
  return v == null ? "" : v > 0 ? "pos" : v < 0 ? "neg" : "";
}

function heatColor(pct) {
  if (pct == null) return "#333";
  if (pct > 2)  return "#00d46a";
  if (pct > 0.5) return "#238636";
  if (pct > 0)  return "#2ea04388";
  if (pct > -0.5) return "#f8514988";
  if (pct > -2) return "#da3633";
  return "#b62324";
}

function ytdBarColor(pct) {
  if (pct == null) return "#333";
  if (pct >= 15) return "#00d46a";
  if (pct >= 5)  return "#3fb950";
  if (pct >= 0)  return "#2ea04388";
  if (pct >= -5) return "#f8514988";
  if (pct >= -15) return "#da3633";
  return "#b62324";
}

function ytdBarWidth(pct) {
  if (pct == null) return "50%";
  const clamped = Math.max(-40, Math.min(40, pct));
  return ((clamped + 40) / 80 * 100).toFixed(1) + "%";
}

async function fetchPerformance(refresh = false) {
  loader.classList.remove("hidden");
  grid.innerHTML = "";
  heatStrip.innerHTML = "";

  const params = new URLSearchParams();
  if (refresh) params.set("refresh", "true");

  const res = await fetch("/api/performance?" + params);
  if (!res.ok) throw new Error("HTTP " + res.status);
  const json = await res.json();

  data = json.signals;
  const d = new Date(json.date);
  dateLabel.textContent = d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  mockBadge.style.display = json.is_mock ? "inline-flex" : "none";

  renderAll();
  loader.classList.add("hidden");
}

function sortedItems() {
  return Object.values(data)
    .filter(d => !d.error)
    .sort((a, b) => {
      const av = sortMode === "ytd" ? (a.ytd_change_pct ?? -999) : (a.today_change_pct ?? -999);
      const bv = sortMode === "ytd" ? (b.ytd_change_pct ?? -999) : (b.today_change_pct ?? -999);
      return bv - av;
    });
}

function renderAll() {
  const sorted = sortedItems();
  renderHeatStrip(sorted);
  grid.innerHTML = "";
  sorted.forEach(renderCard);
}

function renderHeatStrip(items) {
  heatStrip.innerHTML = "";
  items.forEach(d => {
    const pct = sortMode === "ytd" ? d.ytd_change_pct : d.today_change_pct;
    const cell = document.createElement("div");
    cell.className = "heat-cell";
    cell.style.background = heatColor(pct);
    cell.style.color = (pct != null && Math.abs(pct) < 0.5) ? "#ccc" : "#fff";
    cell.innerHTML = `<span class="hs-sym">${d.symbol}</span><span class="hs-pct">${fmtPct(pct, 1)}</span>`;
    cell.onclick = () => showDetail(d.symbol);
    heatStrip.appendChild(cell);
  });
}

function renderCard(d) {
  const todayCls = pctCls(d.today_change_pct);
  const ytdCls = pctCls(d.ytd_change_pct);
  const ytdPct = d.ytd_change_pct;
  const barW = ytdBarWidth(ytdPct);
  const barC = ytdBarColor(ytdPct);

  const card = document.createElement("div");
  card.className = "card";
  card.style.borderLeftColor = ETF_META[d.symbol]?.color || "transparent";
  card.style.borderLeftWidth = "3px";
  card.innerHTML = `
    <div class="card-top">
      <span class="card-sym">${d.symbol}</span>
      <span class="perf-today-badge ${todayCls}">${fmtPct(d.today_change_pct, 2)}</span>
    </div>
    <div class="card-name">${d.name || d.symbol}</div>
    <div class="card-row">
      <span class="card-price">$${fmt(d.price)}</span>
      <span class="card-sub">prev $${fmt(d.prev_close)}</span>
    </div>
    <div class="ytd-row">
      <span class="ytd-label">YTD</span>
      <span class="ytd-pct ${ytdCls}">${fmtPct(ytdPct, 2)}</span>
    </div>
    <div class="ytd-bar-track">
      <div class="ytd-bar-mid"></div>
      <div class="ytd-bar-fill" style="width:${barW};background:${barC}"></div>
    </div>
    <div class="ytd-meta">
      <span>Start $${fmt(d.ytd_start_price)}</span>
      <span>${d.ytd_start_year || "—"}</span>
    </div>
  `;
  card.onclick = () => showDetail(d.symbol);
  grid.appendChild(card);
}

function showDetail(sym) {
  const d = data[sym];
  if (!d || d.error) return;

  const todayCls = pctCls(d.today_change_pct);
  const ytdCls = pctCls(d.ytd_change_pct);

  const html = `
    <div class="dt-header">
      <div class="dt-sym">${d.symbol}</div>
      <div class="dt-name">${d.name}</div>
      <div class="dt-sector">${d.sector}</div>
    </div>

    <div class="dt-section">Today's Performance (${d.last_date || ""})</div>
    <div class="dt-row"><span class="label">Last Price</span><span class="val">$${fmt(d.price)}</span></div>
    <div class="dt-row"><span class="label">Prev Close</span><span class="val">$${fmt(d.prev_close)}</span></div>
    <div class="dt-row"><span class="label">Change</span><span class="val ${todayCls}">${fmtPct(d.today_change_pct)}</span></div>
    <div class="dt-row"><span class="label">Open</span><span class="val">$${fmt(d.today_open)}</span></div>
    <div class="dt-row"><span class="label">High</span><span class="val">$${fmt(d.today_high)}</span></div>
    <div class="dt-row"><span class="label">Low</span><span class="val">$${fmt(d.today_low)}</span></div>
    <div class="dt-row"><span class="label">Volume</span><span class="val">${d.today_volume ? d.today_volume.toLocaleString() : "—"}</span></div>

    <div class="dt-section">Year-to-Date Performance (${d.ytd_start_year || ""})</div>
    <div class="dt-row"><span class="label">YTD Return</span><span class="val ${ytdCls}">${fmtPct(d.ytd_change_pct)}</span></div>
    <div class="dt-row"><span class="label">Start of Year Price</span><span class="val">$${fmt(d.ytd_start_price)}</span></div>
    <div class="dt-row"><span class="label">Current Price</span><span class="val">$${fmt(d.price)}</span></div>
    <div class="dt-row"><span class="label">YTD High</span><span class="val">$${fmt(d.ytd_high)}</span></div>
    <div class="dt-row"><span class="label">YTD Low</span><span class="val">$${fmt(d.ytd_low)}</span></div>
    <div class="dt-row"><span class="label">YTD Range</span><span class="val">$${fmt(d.ytd_low)} – $${fmt(d.ytd_high)}</span></div>
  `;

  detailContent.innerHTML = html;
  overlay.classList.add("open");
}

// Sort tabs
document.getElementById("sort-today").onclick = function() {
  sortMode = "today";
  this.classList.add("active");
  document.getElementById("sort-ytd").classList.remove("active");
  renderAll();
};
document.getElementById("sort-ytd").onclick = function() {
  sortMode = "ytd";
  this.classList.add("active");
  document.getElementById("sort-today").classList.remove("active");
  renderAll();
};

// Close detail
document.getElementById("detail-close").onclick = () => overlay.classList.remove("open");
overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
document.addEventListener("keydown", e => { if (e.key === "Escape") overlay.classList.remove("open"); });

document.getElementById("btn-refresh").onclick = () => fetchPerformance(true);

// Boot
fetchPerformance();
