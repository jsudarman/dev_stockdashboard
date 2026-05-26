"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let currentDate  = null;
let latestData   = {};
let prevDate     = null;
let nextDate     = null;
let isToday      = true;
let isMockMode   = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const overlay    = document.getElementById("loading-overlay");
const errBanner  = document.getElementById("error-banner");
const dateEl     = document.getElementById("date-display");
const btnPrev    = document.getElementById("btn-prev");
const btnNext    = document.getElementById("btn-next");
const btnRefresh = document.getElementById("btn-refresh");
const lastUpdate = document.getElementById("last-update");
const mockBadge  = document.getElementById("mock-mode-badge");
const tooltip    = document.getElementById("etf-tooltip");

// ── Signal helpers ───────────────────────────────────────────────────────────
function sigClass(s) {
  if (s > 0) return "ind-bull";
  if (s < 0) return "ind-bear";
  return "ind-neut";
}
function badgeClass(cssClass) {
  return "badge-" + (cssClass || "unavailable");
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
function fmtNum(v, dec=2) {
  if (v == null) return "—";
  return Number(v).toFixed(dec);
}

// ── Mock mode banner ─────────────────────────────────────────────────────────
function renderMockMode(isMock) {
  isMockMode = isMock;
  if (!mockBadge) return;
  if (isMock) {
    mockBadge.style.display = "inline-flex";
  } else {
    mockBadge.style.display = "none";
  }
  document.querySelectorAll(".etf-card").forEach(card => {
    card.classList.toggle("is-mock", isMock);
  });
}

// ── Render cards ───────────────────────────────────────────────────────────────
function renderCard(sig) {
  const sym  = sig.symbol;
  const card = document.getElementById("card-" + sym);
  if (!card) return;
  card.classList.remove("skeleton");
  card.classList.toggle("is-mock", isMockMode);

  if (sig.error) {
    document.getElementById("badge-" + sym).textContent = "N/A";
    document.getElementById("badge-" + sym).className   = "card-signal-badge badge-unavailable";
    document.getElementById("price-" + sym).textContent = "—";
    document.getElementById("change-" + sym).textContent= "error";
    return;
  }

  const badge = document.getElementById("badge-" + sym);
  badge.textContent = sig.label;
  badge.className   = "card-signal-badge " + badgeClass(sig.css_class);

  document.getElementById("price-" + sym).textContent = "$" + fmtNum(sig.price);

  const chEl = document.getElementById("change-" + sym);
  const pct  = sig.price_change_pct;
  chEl.textContent = (pct >= 0 ? "+" : "") + fmtNum(pct) + "%";
  chEl.className   = "card-change " + (pct >= 0 ? "pos" : "neg");

  document.getElementById("fill-" + sym).style.width      = scoreToWidth(sig.score);
  document.getElementById("fill-" + sym).style.background = scoreToColor(sig.score);
  document.getElementById("score-" + sym).textContent     = sig.score + "/8";

  if (sig.indicators) {
    const ind = sig.indicators;
    const rows = [
      ["rsi",  ind.RSI,            fmtNum(ind.RSI?.value)],
      ["ema",  ind["EMA 9/20"],    ind["EMA 9/20"]?.value || "—"],
      ["vwap", ind.VWAP,           ind.VWAP?.value ? "$" + fmtNum(ind.VWAP.value) : "—"],
      ["vol",  ind.Volume,         ind.Volume?.value ? ind.Volume.value + "×" : "—"],
      ["pcr",  ind.PCR,            fmtNum(ind.PCR?.value)],
      ["cmf",  ind.CMF,            fmtNum(ind.CMF?.value, 3)],
      ["mfi",  ind.MFI,            fmtNum(ind.MFI?.value)],
      ["div",  ind["MFI Divergence"], ["−1","0","+1"][ind["MFI Divergence"]?.value + 1] || "—"],
    ];
    rows.forEach(([id, obj, val]) => {
      const el = document.getElementById(id + "-" + sym);
      if (!el || !obj) return;
      el.textContent = val;
      el.className   = "ind-dot " + sigClass(obj.signal);
    });
  }

  card.onclick = (e) => {
    if (e.target.tagName === "A") return;
    window.location.href = "/etf/" + sym;
  };
}

// ── VIX ────────────────────────────────────────────────────────────────────────────
function renderVIX(vix, isMock) {
  const valEl  = document.getElementById("vix-value");
  const sentEl = document.getElementById("vix-sentiment");
  const panel  = document.getElementById("vix-panel");
  const mockEl = document.getElementById("vix-mock-tag");

  if (!vix || vix.value == null) {
    valEl.textContent  = "—";
    sentEl.textContent = "Unavailable";
    return;
  }
  valEl.textContent  = vix.value;
  sentEl.textContent = vix.sentiment + " (" + (vix.change >= 0 ? "+" : "") + vix.change + ")";

  const v = vix.value;
  if (v < 15) {
    valEl.style.color  = "#00d46a";
    panel.style.border = "1px solid #00d46a44";
  } else if (v > 25) {
    valEl.style.color  = "#ff3333";
    panel.style.border = "1px solid #ff333344";
  } else {
    valEl.style.color  = "#f7c948";
    panel.style.border = "1px solid #f7c94844";
  }

  if (mockEl) mockEl.style.display = isMock ? "inline" : "none";
}

// ── Fetch & Render ─────────────────────────────────────────────────────────────
async function fetchSignals(date, refresh=false) {
  showLoading(true);
  hideError();
  try {
    const url = `/api/signals?date=${date}&refresh=${refresh}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();

    currentDate = json.date;
    prevDate    = json.prev_date;
    nextDate    = json.next_date;
    isToday     = json.is_today;
    latestData  = json.signals;

    dateEl.textContent = currentDate;
    btnNext.disabled   = isToday;

    const mock = !!json.is_mock;
    renderMockMode(mock);
    lastUpdate.textContent = "Updated " + new Date().toLocaleTimeString()
      + (mock ? " · SIMULATED DATA" : " · Live data");

    renderVIX(json.vix, mock);
    Object.values(json.signals).forEach(renderCard);
  } catch (e) {
    showError("Failed to load data: " + e.message);
  } finally {
    showLoading(false);
  }
}

// ── Controls ──────────────────────────────────────────────────────────────────
btnPrev.addEventListener("click", () => {
  if (prevDate) fetchSignals(prevDate, false);
});
btnNext.addEventListener("click", () => {
  if (nextDate && !isToday) fetchSignals(nextDate, false);
});
btnRefresh.addEventListener("click", () => {
  const icon = document.getElementById("refresh-icon");
  icon.style.display = "none";
  btnRefresh.disabled = true;
  fetchSignals(currentDate || todayStr(), true).finally(() => {
    icon.style.display = "";
    btnRefresh.disabled = false;
  });
});

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

// ── Tooltip ─────────────────────────────────────────────────────────────────────
let tooltipTimer = null;

document.querySelectorAll(".etf-card").forEach(card => {
  card.addEventListener("mouseenter", (e) => {
    const sym = card.dataset.symbol;
    tooltipTimer = setTimeout(() => showTooltip(card, sym, e), 200);
  });
  card.addEventListener("mousemove", moveTooltip);
  card.addEventListener("mouseleave", () => {
    clearTimeout(tooltipTimer);
    tooltip.style.display = "none";
  });
});

function showTooltip(card, sym, e) {
  const sig  = latestData[sym];
  const info = ETF_INFO[sym] || {};

  document.getElementById("tt-ticker").textContent = sym;
  document.getElementById("tt-name").textContent   = info.name || sym;
  document.getElementById("tt-sector").textContent = info.sector || "";
  document.getElementById("tt-desc").textContent   = info.description || "";

  const ttMock = document.getElementById("tt-mock-note");
  if (ttMock) ttMock.style.display = isMockMode ? "block" : "none";

  const ttBadge = document.getElementById("tt-badge");
  if (sig && !sig.error) {
    ttBadge.textContent = sig.label || "—";
    ttBadge.className   = "tt-badge " + badgeClass(sig.css_class);
    populateList("tt-bullish", sig.bullish_reasons || []);
    populateList("tt-bearish", sig.bearish_reasons || []);
    populateList("tt-neutral", sig.neutral_reasons || []);
  } else {
    ttBadge.textContent = "N/A";
    ttBadge.className   = "tt-badge badge-unavailable";
    populateList("tt-bullish", []);
    populateList("tt-bearish", []);
    populateList("tt-neutral", ["Data unavailable for this symbol"]);
  }

  tooltip.style.display = "block";
  positionTooltip(e);
}

function moveTooltip(e) {
  if (tooltip.style.display === "block") positionTooltip(e);
}

function positionTooltip(e) {
  const tw  = tooltip.offsetWidth  || 320;
  const th  = tooltip.offsetHeight || 300;
  const vw  = window.innerWidth;
  const vh  = window.innerHeight;
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

// ── Util ───────────────────────────────────────────────────────────────────────────
function showLoading(on) {
  overlay.classList.toggle("hidden", !on);
}
function showError(msg) {
  errBanner.textContent = msg;
  errBanner.style.display = "block";
}
function hideError() {
  errBanner.style.display = "none";
}

// ── Boot ────────────────────────────────────────────────────────────────────────────
fetchSignals(todayStr(), false);
