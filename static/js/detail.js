"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let currentDate = null;
let prevDate    = null;
let nextDate    = null;
let isToday     = true;
let latestData  = null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const dateEl    = document.getElementById("detail-date");
const btnPrev   = document.getElementById("btn-prev-d");
const btnNext   = document.getElementById("btn-next-d");
const btnRef    = document.getElementById("btn-refresh-d");
const tooltip   = document.getElementById("holding-tooltip");

// ── Helpers ──────────────────────────────────────────────────────────────────────
function fmtNum(v, dec=2) {
  if (v == null || isNaN(v)) return "—";
  return Number(v).toFixed(dec);
}
function badgeClass(cssClass) {
  return "badge-" + (cssClass || "unavailable");
}
function sigCls(s) {
  if (s > 0) return "bull";
  if (s < 0) return "bear";
  return "neut";
}
function scoreToWidth(score) {
  return ((score + 8) / 16 * 100).toFixed(1) + "%";
}
function scoreToColor(score) {
  if (score >= 5)  return "#00d46a";
  if (score >= 3)  return "#43e97b";
  if (score >= -2) return "#f7c948";
  if (score >= -4) return "#ff6b6b";
  return "#ff3333";
}
function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

// ── Render ETF header ───────────────────────────────────────────────────────────
function renderETFHeader(data) {
  const info = data.info || {};
  document.getElementById("detail-etf-name").textContent   = info.name        || SYMBOL;
  document.getElementById("detail-etf-sector").textContent = info.sector      || "";
  document.getElementById("detail-etf-desc").textContent   = info.description || "";

  const sig = data.etf_signal;
  if (sig && !sig.error) {
    const badge = document.getElementById("detail-badge");
    badge.textContent = sig.label;
    badge.className   = "dsb-badge " + sigCls(sig.score === 0 ? 0 : (sig.score > 0 ? 1 : -1));
    badge.style.color = sig.color;
    document.getElementById("detail-score").textContent = `Score: ${sig.score}/8`;
    document.getElementById("detail-price").textContent = sig.price ? `$${fmtNum(sig.price)}  ${sig.price_change_pct >= 0 ? "+" : ""}${fmtNum(sig.price_change_pct)}%` : "—";
  }
}

// ── Render indicator breakdown ────────────────────────────────────────────────────────
function renderIndicatorBreakdown(sig) {
  const container = document.getElementById("etf-ind-breakdown");
  if (!sig || sig.error || !sig.indicators) {
    container.innerHTML = `<div class="error-banner">Indicator data unavailable: ${sig?.error || "unknown"}</div>`;
    return;
  }
  container.innerHTML = "";
  Object.entries(sig.indicators).forEach(([name, obj]) => {
    const s    = obj.signal;
    const card = document.createElement("div");
    card.className = "ind-card";
    const val = formatIndicatorValue(name, obj.value);
    card.innerHTML = `
      <div class="ind-card-header">
        <span class="ind-card-name">${name}</span>
        <div style="display:flex;align-items:center;gap:.5rem">
          <span class="ind-card-val">${val}</span>
          <span class="ind-card-signal ${sigCls(s)}">${s > 0 ? "▲ Bull" : s < 0 ? "▼ Bear" : "– Neut"}</span>
        </div>
      </div>
      <div class="ind-card-reason">${obj.reasoning || ""}</div>
    `;
    container.appendChild(card);
  });
}

function formatIndicatorValue(name, val) {
  if (val == null) return "—";
  if (name === "VWAP")           return "$" + fmtNum(val);
  if (name === "Volume")         return fmtNum(val) + "×";
  if (name === "MFI Divergence") return ["-1 (Bear)", "0 (None)", "+1 (Bull)"][val + 1] || "—";
  if (name === "EMA 9/20")       return val;
  if (typeof val === "number")   return fmtNum(val);
  return String(val);
}

// ── Render holdings grid ─────────────────────────────────────────────────────────────
function renderHoldings(data) {
  const loadEl = document.getElementById("holdings-loading");
  const errEl  = document.getElementById("holdings-error");
  const grid   = document.getElementById("holdings-grid");
  loadEl.style.display = "none";
  grid.innerHTML = "";

  const holdings = data.info?.holdings || [];
  const signals  = data.holding_signals || {};

  if (!holdings.length) {
    grid.innerHTML = "<p style='color:var(--text-muted)'>No holdings data available.</p>";
    return;
  }

  holdings.forEach((h, idx) => {
    const ticker = h.ticker;
    const name   = h.name;
    const sig    = signals[ticker];
    const card   = document.createElement("div");
    card.className = "holding-card";
    card.dataset.ticker = ticker;

    if (!sig || sig.error) {
      card.innerHTML = `
        <div class="holding-header">
          <span class="holding-ticker">${ticker}</span>
          <span class="holding-badge badge-unavailable">N/A</span>
        </div>
        <div class="holding-name">${name}</div>
        <div style="color:var(--text-dim);font-size:.8rem">Data unavailable</div>
      `;
    } else {
      const pct = sig.price_change_pct;
      const indPips = sig.indicators ? Object.entries(sig.indicators).map(([n, obj]) => {
        const abbr = indAbbr(n);
        return `<span class="ind-pip ${sigCls(obj.signal)}" title="${n}: ${obj.reasoning}">${abbr}</span>`;
      }).join("") : "";

      card.innerHTML = `
        <div class="holding-header">
          <span class="holding-ticker">${ticker}</span>
          <span class="holding-badge ${badgeClass(sig.css_class)}">${sig.label}</span>
        </div>
        <div class="holding-name">${name}</div>
        <div class="holding-price-row">
          <span class="holding-price">$${fmtNum(sig.price)}</span>
          <span class="holding-change ${pct >= 0 ? "pos" : "neg"}">${pct >= 0 ? "+" : ""}${fmtNum(pct)}%</span>
        </div>
        <div class="holding-score-bar">
          <div class="score-track" style="flex:1">
            <div class="score-fill" style="width:${scoreToWidth(sig.score)};background:${scoreToColor(sig.score)}"></div>
          </div>
          <span class="score-label" style="font-size:.72rem;color:var(--text-muted);min-width:28px;text-align:right">${sig.score}/8</span>
        </div>
        <div class="holding-ind-mini">${indPips}</div>
      `;

      card.addEventListener("mouseenter", (e) => showHoldingTooltip(card, ticker, name, sig, e));
      card.addEventListener("mousemove", moveHoldingTooltip);
      card.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
    }

    grid.appendChild(card);
  });
}

function indAbbr(name) {
  const map = {
    "RSI": "RSI", "EMA 9/20": "EMA", "VWAP": "VWAP",
    "Volume": "VOL", "PCR": "PCR", "CMF": "CMF",
    "MFI": "MFI", "MFI Divergence": "DIV",
  };
  return map[name] || name.slice(0, 3).toUpperCase();
}

// ── Holding Tooltip ──────────────────────────────────────────────────────────────
function showHoldingTooltip(card, ticker, name, sig, e) {
  document.getElementById("ht-ticker").textContent = ticker;
  document.getElementById("ht-name").textContent   = name;
  const badge = document.getElementById("ht-badge");
  badge.textContent = sig.label;
  badge.className   = "tt-badge " + badgeClass(sig.css_class);
  populateList("ht-bullish", sig.bullish_reasons || []);
  populateList("ht-bearish", sig.bearish_reasons || []);
  populateList("ht-neutral", sig.neutral_reasons || []);
  tooltip.style.display = "block";
  positionTooltip(e);
}

function moveHoldingTooltip(e) {
  if (tooltip.style.display === "block") positionTooltip(e);
}

function positionTooltip(e) {
  const tw = tooltip.offsetWidth  || 320;
  const th = tooltip.offsetHeight || 250;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let x = e.clientX + 16;
  let y = e.clientY + 16;
  if (x + tw > vw - 12) x = e.clientX - tw - 16;
  if (y + th > vh - 12) y = e.clientY - th - 16;
  tooltip.style.left = x + "px";
  tooltip.style.top  = y + "px";
}

function populateList(id, items) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.style.color = "#555";
    li.textContent = "None";
    ul.appendChild(li);
    return;
  }
  items.forEach(text => {
    const li = document.createElement("li");
    li.textContent = text;
    ul.appendChild(li);
  });
}

// ── Mock mode ───────────────────────────────────────────────────────────────────
function applyMockMode(isMock) {
  const badge = document.getElementById("detail-mock-badge");
  if (badge) badge.style.display = isMock ? "inline-flex" : "none";
  const note = document.getElementById("detail-mock-note");
  if (note) note.style.display = isMock ? "block" : "none";
  document.querySelectorAll(".holding-card").forEach(c => c.classList.toggle("is-mock", isMock));
  document.querySelectorAll(".ind-card").forEach(c => c.classList.toggle("is-mock", isMock));
}

// ── Fetch ────────────────────────────────────────────────────────────────────────────
async function fetchDetail(date, refresh=false) {
  document.getElementById("holdings-loading").style.display = "block";
  document.getElementById("holdings-loading").textContent = "Fetching data…";
  document.getElementById("holdings-grid").innerHTML = "";

  try {
    const res  = await fetch(`/api/etf/${SYMBOL}?date=${date}&refresh=${refresh}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    latestData = data;
    currentDate = data.date;
    dateEl.textContent = currentDate;

    renderETFHeader(data);
    renderIndicatorBreakdown(data.etf_signal);
    renderHoldings(data);
    applyMockMode(!!data.is_mock);
  } catch(e) {
    document.getElementById("holdings-loading").style.display = "none";
    document.getElementById("holdings-error").textContent = "Error: " + e.message;
    document.getElementById("holdings-error").style.display = "block";
  }
}

// ── Controls ──────────────────────────────────────────────────────────────────
function prevTradingDate(d) {
  const dt = new Date(d);
  dt.setDate(dt.getDate() - 1);
  while (dt.getDay() === 0 || dt.getDay() === 6) dt.setDate(dt.getDate() - 1);
  return dt.toISOString().slice(0, 10);
}
function nextTradingDate(d) {
  const dt = new Date(d);
  dt.setDate(dt.getDate() + 1);
  while (dt.getDay() === 0 || dt.getDay() === 6) dt.setDate(dt.getDate() + 1);
  const today = new Date().toISOString().slice(0, 10);
  return dt.toISOString().slice(0, 10) > today ? d : dt.toISOString().slice(0, 10);
}

btnPrev.addEventListener("click", () => {
  if (currentDate) fetchDetail(prevTradingDate(currentDate), false);
});
btnNext.addEventListener("click", () => {
  if (currentDate) {
    const nd = nextTradingDate(currentDate);
    if (nd !== currentDate) fetchDetail(nd, false);
  }
});
btnRef.addEventListener("click", () => fetchDetail(currentDate || todayStr(), true));

// ── Boot ────────────────────────────────────────────────────────────────────────────
fetchDetail(todayStr(), false);
