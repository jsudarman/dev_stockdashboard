from __future__ import annotations
import logging
from src.indicators import compute_all

logger = logging.getLogger(__name__)


def _rsi_signal(rsi: float | None) -> tuple[int, str]:
    if rsi is None:
        return 0, "RSI data unavailable"
    if rsi < 30:
        return 1, f"RSI {rsi:.1f} — Oversold (< 30): bullish mean-reversion setup"
    if rsi > 70:
        return -1, f"RSI {rsi:.1f} — Overbought (> 70): bearish exhaustion signal"
    if rsi < 45:
        return 0, f"RSI {rsi:.1f} — Neutral/slightly weak"
    if rsi > 55:
        return 0, f"RSI {rsi:.1f} — Neutral/slightly strong"
    return 0, f"RSI {rsi:.1f} — Neutral zone (30-70)"


def _ema_signal(ema9: float | None, ema20: float | None, close: float) -> tuple[int, str]:
    if ema9 is None or ema20 is None:
        return 0, "EMA data unavailable"
    if ema9 > ema20:
        spread = round((ema9 - ema20) / ema20 * 100, 2)
        return 1, f"EMA9 ({ema9:.2f}) > EMA20 ({ema20:.2f}) — Bullish crossover (+{spread}% spread)"
    else:
        spread = round((ema20 - ema9) / ema20 * 100, 2)
        return -1, f"EMA9 ({ema9:.2f}) < EMA20 ({ema20:.2f}) — Bearish crossover (-{spread}% spread)"


def _vwap_signal(close: float, vwap: float | None) -> tuple[int, str]:
    if vwap is None:
        return 0, "VWAP unavailable (market may be closed or no intraday data)"
    if close > vwap:
        pct = round((close - vwap) / vwap * 100, 2)
        return 1, f"Price (${close}) above VWAP (${vwap:.2f}) by +{pct}% — Bullish intraday"
    else:
        pct = round((vwap - close) / vwap * 100, 2)
        return -1, f"Price (${close}) below VWAP (${vwap:.2f}) by -{pct}% — Bearish intraday"


def _volume_signal(vol_ratio: float | None, close: float, open_: float) -> tuple[int, str]:
    if vol_ratio is None:
        return 0, "Volume data unavailable"
    is_green = close >= open_
    if vol_ratio >= 1.5:
        if is_green:
            return 1, f"Volume {vol_ratio:.2f}x avg on UP day — Strong buying conviction"
        else:
            return -1, f"Volume {vol_ratio:.2f}x avg on DOWN day — Heavy distribution/selling"
    elif vol_ratio >= 1.1:
        if is_green:
            return 0, f"Volume slightly above avg ({vol_ratio:.2f}x) on up day — Mild bullish"
        else:
            return 0, f"Volume slightly above avg ({vol_ratio:.2f}x) on down day — Mild bearish"
    else:
        return 0, f"Volume below avg ({vol_ratio:.2f}x) — Low conviction, wait for confirmation"


def _pcr_signal(pcr: float | None) -> tuple[int, str]:
    if pcr is None:
        return 0, "PCR unavailable (no options data for this symbol)"
    if pcr < 0.7:
        return 1, f"PCR {pcr:.2f} < 0.7 — Calls dominate: bullish sentiment, possible short squeeze"
    if pcr > 1.0:
        return -1, f"PCR {pcr:.2f} > 1.0 — Puts dominate: bearish hedging, elevated downside risk"
    return 0, f"PCR {pcr:.2f} in 0.7-1.0 — Neutral options sentiment"


def _cmf_signal(cmf: float | None) -> tuple[int, str]:
    if cmf is None:
        return 0, "CMF data unavailable"
    if cmf > 0.1:
        return 1, f"CMF {cmf:.3f} > 0.1 — Money flowing IN: institutional accumulation"
    if cmf < -0.1:
        return -1, f"CMF {cmf:.3f} < -0.1 — Money flowing OUT: institutional distribution"
    return 0, f"CMF {cmf:.3f} — Neutral money flow (-0.1 to +0.1)"


def _mfi_signal(mfi: float | None) -> tuple[int, str]:
    if mfi is None:
        return 0, "MFI data unavailable"
    if mfi < 20:
        return 1, f"MFI {mfi:.1f} < 20 — Oversold with volume: strong bullish reversal candidate"
    if mfi > 80:
        return -1, f"MFI {mfi:.1f} > 80 — Overbought with volume: distribution likely"
    return 0, f"MFI {mfi:.1f} — Neutral zone (20-80)"


def _mfi_div_signal(div: int) -> tuple[int, str]:
    if div == 1:
        return 1, "Bullish MFI divergence: price made lower low but MFI made higher low — hidden strength"
    if div == -1:
        return -1, "Bearish MFI divergence: price made higher high but MFI made lower high — hidden weakness"
    return 0, "No MFI divergence detected — trend is confirmed by money flow"


SCORE_LABELS = {
    (5, 8):  ("Strong Buy",   "strong-buy",   "#00d46a"),
    (3, 4):  ("Buy",          "buy",           "#43e97b"),
    (-2, 2): ("Hold",         "hold",          "#f7c948"),
    (-4,-3): ("Sell",         "sell",          "#ff6b6b"),
    (-8,-5): ("Strong Sell",  "strong-sell",   "#ff3333"),
}


def score_to_label(score: int) -> tuple[str, str, str]:
    for (lo, hi), info in SCORE_LABELS.items():
        if lo <= score <= hi:
            return info
    return ("Hold", "hold", "#f7c948")


def calculate_signals(symbol: str, df_daily, df_intraday, pcr: float | None) -> dict:
    try:
        ind = compute_all(df_daily, df_intraday, pcr)
    except Exception as e:
        logger.error(f"compute_all {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}

    close = ind["close"]
    open_ = ind["open"]

    s_rsi,    r_rsi    = _rsi_signal(ind["rsi"])
    s_ema,    r_ema    = _ema_signal(ind["ema9"], ind["ema20"], close)
    s_vwap,   r_vwap   = _vwap_signal(close, ind["vwap"])
    s_vol,    r_vol    = _volume_signal(ind["vol_ratio"], close, open_)
    s_pcr,    r_pcr    = _pcr_signal(ind["pcr"])
    s_cmf,    r_cmf    = _cmf_signal(ind["cmf"])
    s_mfi,    r_mfi    = _mfi_signal(ind["mfi"])
    s_div,    r_div    = _mfi_div_signal(ind["mfi_divergence"])

    score = s_rsi + s_ema + s_vwap + s_vol + s_pcr + s_cmf + s_mfi + s_div
    label, css_class, color = score_to_label(score)

    bullish = [r for s, r in [(s_rsi,r_rsi),(s_ema,r_ema),(s_vwap,r_vwap),(s_vol,r_vol),
                               (s_pcr,r_pcr),(s_cmf,r_cmf),(s_mfi,r_mfi),(s_div,r_div)] if s > 0]
    bearish = [r for s, r in [(s_rsi,r_rsi),(s_ema,r_ema),(s_vwap,r_vwap),(s_vol,r_vol),
                               (s_pcr,r_pcr),(s_cmf,r_cmf),(s_mfi,r_mfi),(s_div,r_div)] if s < 0]
    neutral = [r for s, r in [(s_rsi,r_rsi),(s_ema,r_ema),(s_vwap,r_vwap),(s_vol,r_vol),
                               (s_pcr,r_pcr),(s_cmf,r_cmf),(s_mfi,r_mfi),(s_div,r_div)] if s == 0]

    return {
        "symbol":    symbol,
        "score":     score,
        "label":     label,
        "css_class": css_class,
        "color":     color,
        "indicators": {
            "RSI":           {"value": ind["rsi"],      "signal": s_rsi,  "reasoning": r_rsi},
            "EMA 9/20":      {"value": f"{ind['ema9']}/{ind['ema20']}", "signal": s_ema,  "reasoning": r_ema},
            "VWAP":          {"value": ind["vwap"],     "signal": s_vwap, "reasoning": r_vwap},
            "Volume":        {"value": ind["vol_ratio"],"signal": s_vol,  "reasoning": r_vol},
            "PCR":           {"value": ind["pcr"],      "signal": s_pcr,  "reasoning": r_pcr},
            "CMF":           {"value": ind["cmf"],      "signal": s_cmf,  "reasoning": r_cmf},
            "MFI":           {"value": ind["mfi"],      "signal": s_mfi,  "reasoning": r_mfi},
            "MFI Divergence":{"value": ind["mfi_divergence"], "signal": s_div, "reasoning": r_div},
        },
        "bullish_reasons": bullish,
        "bearish_reasons": bearish,
        "neutral_reasons": neutral,
        "price":            ind["close"],
        "price_change_pct": ind["price_change_pct"],
        "volume":           ind["volume"],
        "avg_volume":       ind["avg_volume"],
        "vol_ratio":        ind["vol_ratio"],
    }
