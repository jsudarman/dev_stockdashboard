"use strict";

let currentEndDate = null;
let allData = {};

const sections = document.getElementById("etf-sections");
const loader = document.getElementById("loader");
const weekLabel = document.getElementById("week-label");
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

async function fetchTopStocks(endDate, refresh = false) {
  loader.classList.remove("hidden");
  sections.innerHTML = "";
  allData = {};

  const etfOrder = Object.keys(ETF_META);

  for (const etfSym of etfOrder) {
    const params = new URLSearchParams();
    params.set("etf", etfSym);
    if (endDate) params.set("end_date", endDate);
    if (refresh) params.set("refresh", "true");

    try {
      const res = await fetch("/api/top-stocks?" + params);
      if (!res.ok) continue;
      const json = await res.json();

      if (!currentEndDate) {
        currentEndDate = json.end_date;
        weekLabel.textContent = json.week_label;
        mockBadge.style.display = json.is_mock ? "inline-flex" : "none";
      }

      if (json.top_stocks && json.top_stocks.length) {
        allData[etfSym] = json;
      }
    } catch (e) {
      console.error(`Failed to load ${etfSym}:`, e);
    }
  }

  // Sort ETF sections by best (top #1) stock's 5-day performance, best first
  const sorted = Object.values(allData).sort((a, b) => {
    const aPct = a.top_stocks[0]?.signal?.weekly_change_pct ?? -999;
    const bPct = b.top_stocks[0]?.signal?.weekly_change_pct ?? -999;
    return bPct - aPct;
  });

  sections.innerHTML = "";
  sorted.forEach(etf => renderEtfSection(etf));
  loader.classList.add("hidden");
}

function renderEtfSection(etf) {
  const section = document.createElement("div");
  section.className = "ts-section";

  const header = document.createElement("div");
  header.className = "ts-header";
  header.style.borderLeftColor = etf.etf_color;
  header.innerHTML = `
    <span class="ts-etf-sym">${etf.etf_symbol}</span>
    <span class="ts-etf-name">${etf.etf_name}</span>
    <span class="ts-etf-sector">${etf.etf_sector}</span>
  `;
  section.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "ts-grid";

  etf.top_stocks.forEach((stock, i) => {
    const sig = stock.signal || {};
    const pct = sig.weekly_change_pct;
    const pips = (sig.indicators || []).map(ind =>
      `<span class="pip ${sigCls(ind.signal)}" title="${ind.reason}">${ind.name.split(" ")[0]}</span>`
    ).join("");

    const card = document.createElement("div");
    card.className = "card ts-card";
    card.innerHTML = `
      <div class="ts-rank">#${i + 1}</div>
      <div class="card-top">
        <span class="card-sym">${stock.symbol}</span>
        <span class="card-badge badge-${sig.css_class || "hold"}">${sig.label || "N/A"}</span>
      </div>
      <div class="card-name">${stock.company_name || stock.symbol}</div>
      <div class="card-row">
        <span class="card-price">$${fmt(stock.price)}</span>
        <span class="card-change ${pct >= 0 ? "pos" : "neg"}">${pct != null ? (pct >= 0 ? "+" : "") + fmt(pct) + "% 5d" : "—"}</span>
      </div>
      <div class="score-bar">
        <div class="score-track"><div class="score-fill" style="width:${scoreWidth(sig.score || 0)};background:${scoreColor(sig.score || 0)}"></div></div>
        <span class="score-lbl">${sig.score || 0}/10</span>
      </div>
      <div class="ind-pips">${pips}</div>
    `;
    card.onclick = () => showStockDetail(stock, etf.etf_symbol);
    grid.appendChild(card);
  });

  section.appendChild(grid);
  sections.appendChild(section);
}

function peColor(pe, avgPe) {
  if (pe == null || avgPe == null) return "var(--text)";
  if (pe < avgPe * 0.8) return "var(--green)";
  if (pe > avgPe * 1.2) return "var(--red)";
  return "var(--yellow)";
}

function showStockDetail(stock, etfSym) {
  const sig = stock.signal || {};
  const w = stock.weekly || {};
  const pct = sig.weekly_change_pct;
  const etfData = allData[etfSym] || {};
  const peers = etfData.peer_pe || [];

  const peersWithPe = peers.filter(p => p.pe_ratio != null);
  const avgPe = peersWithPe.length ? peersWithPe.reduce((s, p) => s + p.pe_ratio, 0) / peersWithPe.length : null;

  let html = `
    <div class="dt-header">
      <div class="dt-sym">${stock.symbol}</div>
      <div class="dt-name">${stock.company_name || stock.symbol}</div>
      <div class="dt-sector">${stock.industry || ""} &middot; Holding of ${etfSym}</div>
      <div class="dt-badge"><span class="card-badge badge-${sig.css_class}">${sig.label} (${sig.score})</span></div>
    </div>

    <div class="dt-section">Price</div>
    <div class="dt-row"><span class="label">Current</span><span class="val">$${fmt(stock.price)}</span></div>
    <div class="dt-row"><span class="label">5-Day Change</span><span class="val" style="color:${pct >= 0 ? "var(--green)" : "var(--red)"}">${pct != null ? (pct >= 0 ? "+" : "") + fmt(pct) + "%" : "—"}</span></div>

    <div class="dt-section">Valuation</div>
    <div class="dt-row"><span class="label">P/E Ratio</span><span class="val" style="color:${peColor(stock.pe_ratio, avgPe)}">${stock.pe_ratio != null ? fmt(stock.pe_ratio, 1) : "—"}</span></div>
    <div class="dt-row"><span class="label">Peer Avg P/E (${etfSym})</span><span class="val">${avgPe != null ? fmt(avgPe, 1) : "—"}</span></div>
  `;

  if (stock.pe_ratio != null && avgPe != null) {
    const diff = stock.pe_ratio - avgPe;
    const pctDiff = (diff / avgPe * 100);
    const label = diff > 0 ? "above" : "below";
    const color = diff > 0 ? "var(--red)" : "var(--green)";
    html += `<div class="dt-row"><span class="label">vs Peers</span><span class="val" style="color:${color}">${Math.abs(pctDiff).toFixed(1)}% ${label} avg</span></div>`;
  }

  html += `
    <div class="dt-section">Peer P/E Comparison (${etfSym} Holdings)</div>
    <table class="pe-table">
      <tr><th>Ticker</th><th>Company</th><th>P/E</th></tr>
  `;
  peers.sort((a, b) => (a.pe_ratio || 999) - (b.pe_ratio || 999)).forEach(p => {
    const isMe = p.symbol === stock.symbol;
    const rowCls = isMe ? ' class="pe-highlight"' : '';
    html += `<tr${rowCls}><td>${p.symbol}</td><td>${p.company_name}</td><td>${p.pe_ratio != null ? fmt(p.pe_ratio, 1) : "—"}</td></tr>`;
  });
  html += `</table>`;

  html += `
    <div class="dt-section">Last 5 Trading Days OHLCV</div>
    <div class="dt-row"><span class="label">Open</span><span class="val">$${fmt(w.open)}</span></div>
    <div class="dt-row"><span class="label">High</span><span class="val">$${fmt(w.high)}</span></div>
    <div class="dt-row"><span class="label">Low</span><span class="val">$${fmt(w.low)}</span></div>
    <div class="dt-row"><span class="label">Close</span><span class="val">$${fmt(w.close)}</span></div>
    <div class="dt-row"><span class="label">Volume</span><span class="val">${w.volume ? w.volume.toLocaleString() : "—"}</span></div>

    <div class="dt-section">Technical Indicators</div>
    <div class="dt-row"><span class="label">RSI (14)</span><span class="val">${fmt(stock.rsi)}</span></div>
    <div class="dt-row"><span class="label">MACD</span><span class="val">${fmt(stock.macd, 4)}</span></div>
    <div class="dt-row"><span class="label">MACD Signal</span><span class="val">${fmt(stock.macd_signal, 4)}</span></div>
    <div class="dt-row"><span class="label">SMA 20</span><span class="val">$${fmt(stock.sma_20)}</span></div>
    <div class="dt-row"><span class="label">SMA 50</span><span class="val">$${fmt(stock.sma_50)}</span></div>

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
  if (currentEndDate) {
    const d = new Date(currentEndDate);
    d.setDate(d.getDate() - 5);
    fetchTopStocks(d.toISOString().slice(0, 10));
  }
};
document.getElementById("btn-refresh").onclick = () => fetchTopStocks(currentEndDate, true);

// Boot
fetchTopStocks(null);
