"use strict";

let currentWeek = null;
let data = {};

const grid = document.getElementById("grid");
const loader = document.getElementById("loader");
const weekLabel = document.getElementById("week-label");
const heatStrip = document.getElementById("heat-strip");
const mockBadge = document.getElementById("mock-badge");
const overlay = document.getElementById("detail-overlay");
const detailContent = document.getElementById("detail-content");

function fmt(v, d = 2) {
  return v == null ? "—" : Number(v).toFixed(d);
}

function sigCls(s) {
  return s > 0 ? "bull" : s < 0 ? "bear" : "neut";
}

function scoreWidth(score) {
  return ((score + 10) / 20 * 100).toFixed(1) + "%";
}

function scoreColor(score) {
  if (score >= 6) return "#00d46a";
  if (score >= 3) return "#3fb950";
  if (score >= -2) return "#e3b341";
  if (score >= -5) return "#f85149";
  return "#da3633";
}

function heatColor(pct) {
  if (pct == null) return "#333";
  if (pct > 3) return "#00d46a";
  if (pct > 1) return "#238636";
  if (pct > 0) return "#2ea04388";
  if (pct > -1) return "#f8514988";
  if (pct > -3) return "#da3633";
  return "#b62324";
}

// Fetch
async function fetchSignals(week, refresh = false) {
  loader.classList.remove("hidden");
  grid.innerHTML = "";
  heatStrip.innerHTML = "";

  const params = new URLSearchParams();
  if (week) params.set("week", week);
  if (refresh) params.set("refresh", "true");

  const res = await fetch("/api/signals?" + params);
  if (!res.ok) throw new Error("HTTP " + res.status);
  const json = await res.json();

  currentWeek = json.week;
  data = json.signals;

  weekLabel.textContent = json.week_label;
  mockBadge.style.display = json.is_mock ? "inline-flex" : "none";

  // Sort by signal score descending
  const sorted = Object.values(data)
    .filter(d => !d.error)
    .sort((a, b) => (b.signal?.score || 0) - (a.signal?.score || 0));

  renderHeatStrip(sorted);
  sorted.forEach(renderCard);
  loader.classList.add("hidden");
}

// Heat strip
function renderHeatStrip(items) {
  heatStrip.innerHTML = "";
  items.forEach(d => {
    const pct = d.signal?.weekly_change_pct;
    const cell = document.createElement("div");
    cell.className = "heat-cell";
    cell.style.background = heatColor(pct);
    cell.style.color = (pct != null && Math.abs(pct) < 1) ? "#ccc" : "#fff";
    cell.innerHTML = `<span class="hs-sym">${d.symbol}</span><span class="hs-pct">${pct != null ? (pct >= 0 ? "+" : "") + fmt(pct, 1) + "%" : "—"}</span>`;
    cell.onclick = () => showDetail(d.symbol);
    heatStrip.appendChild(cell);
  });
}

// Card
function renderCard(d) {
  const sig = d.signal || {};
  const w = d.weekly;
  const pct = sig.weekly_change_pct;
  const pips = (sig.indicators || []).map(i =>
    `<span class="pip ${sigCls(i.signal)}" title="${i.reason}">${i.name.split(" ")[0]}</span>`
  ).join("");

  const card = document.createElement("div");
  card.className = "card";
  card.style.borderLeftColor = ETF_META[d.symbol]?.color || "transparent";
  card.style.borderLeftWidth = "3px";
  card.innerHTML = `
    <div class="card-top">
      <span class="card-sym">${d.symbol}</span>
      <span class="card-badge badge-${sig.css_class || "hold"}">${sig.label || "N/A"}</span>
    </div>
    <div class="card-name">${d.name || d.symbol}</div>
    <div class="card-row">
      <span class="card-price">$${fmt(d.price)}</span>
      <span class="card-change ${pct >= 0 ? "pos" : "neg"}">${pct != null ? (pct >= 0 ? "+" : "") + fmt(pct) + "% wk" : "—"}</span>
    </div>
    <div class="score-bar">
      <div class="score-track"><div class="score-fill" style="width:${scoreWidth(sig.score || 0)};background:${scoreColor(sig.score || 0)}"></div></div>
      <span class="score-lbl">${sig.score || 0}/10</span>
    </div>
    <div class="ind-pips">${pips}</div>
  `;
  card.onclick = () => showDetail(d.symbol);
  grid.appendChild(card);
}

// Detail panel
function showDetail(sym) {
  const d = data[sym];
  if (!d || d.error) return;
  const sig = d.signal || {};
  const w = d.weekly || {};
  const pct = sig.weekly_change_pct;

  let html = `
    <div class="dt-header">
      <div class="dt-sym">${d.symbol}</div>
      <div class="dt-name">${d.name}</div>
      <div class="dt-sector">${d.sector}</div>
      <div class="dt-badge"><span class="card-badge badge-${sig.css_class}">${sig.label} (${sig.score})</span></div>
    </div>

    <div class="dt-section">Price</div>
    <div class="dt-row"><span class="label">Current</span><span class="val">$${fmt(d.price)}</span></div>
    <div class="dt-row"><span class="label">Weekly Change</span><span class="val" style="color:${pct >= 0 ? "var(--green)" : "var(--red)"}">${pct != null ? (pct >= 0 ? "+" : "") + fmt(pct) + "%" : "—"}</span></div>

    <div class="dt-section">Previous Week OHLCV</div>
    <div class="dt-row"><span class="label">Open</span><span class="val">$${fmt(w.open)}</span></div>
    <div class="dt-row"><span class="label">High</span><span class="val">$${fmt(w.high)}</span></div>
    <div class="dt-row"><span class="label">Low</span><span class="val">$${fmt(w.low)}</span></div>
    <div class="dt-row"><span class="label">Close</span><span class="val">$${fmt(w.close)}</span></div>
    <div class="dt-row"><span class="label">Volume</span><span class="val">${w.volume ? w.volume.toLocaleString() : "—"}</span></div>

    <div class="dt-section">Technical Indicators</div>
    <div class="dt-row"><span class="label">RSI (14)</span><span class="val">${fmt(d.rsi)}</span></div>
    <div class="dt-row"><span class="label">MACD</span><span class="val">${fmt(d.macd, 4)}</span></div>
    <div class="dt-row"><span class="label">MACD Signal</span><span class="val">${fmt(d.macd_signal, 4)}</span></div>
    <div class="dt-row"><span class="label">SMA 20</span><span class="val">$${fmt(d.sma_20)}</span></div>
    <div class="dt-row"><span class="label">SMA 50</span><span class="val">$${fmt(d.sma_50)}</span></div>

    <div class="dt-section">Signal Breakdown</div>
  `;

  (sig.indicators || []).forEach(ind => {
    html += `<div class="dt-ind ${sigCls(ind.signal)}">
      <div class="dt-ind-name">${ind.name}</div>
      <div class="dt-ind-reason">${ind.reason}</div>
    </div>`;
  });

  if (sig.bullish_reasons?.length) {
    html += `<div class="dt-section">Bullish</div>`;
    sig.bullish_reasons.forEach(r => { html += `<div style="font-size:.82rem;color:var(--green);padding:.15rem 0">&#9650; ${r}</div>`; });
  }
  if (sig.bearish_reasons?.length) {
    html += `<div class="dt-section">Bearish</div>`;
    sig.bearish_reasons.forEach(r => { html += `<div style="font-size:.82rem;color:var(--red);padding:.15rem 0">&#9660; ${r}</div>`; });
  }

  detailContent.innerHTML = html;
  overlay.classList.add("open");
}

// Close detail
document.getElementById("detail-close").onclick = () => overlay.classList.remove("open");
overlay.addEventListener("click", e => { if (e.target === overlay) overlay.classList.remove("open"); });
document.addEventListener("keydown", e => { if (e.key === "Escape") overlay.classList.remove("open"); });

// Controls
document.getElementById("btn-prev").onclick = () => {
  if (currentWeek) {
    const d = new Date(currentWeek);
    d.setDate(d.getDate() - 7);
    fetchSignals(d.toISOString().slice(0, 10));
  }
};
document.getElementById("btn-refresh").onclick = () => fetchSignals(currentWeek, true);

// Boot
fetchSignals(null);
