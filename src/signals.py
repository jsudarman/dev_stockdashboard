from __future__ import annotations


def _rsi_signal(rsi_val: float | None) -> tuple[int, str]:
    if rsi_val is None:
        return 0, "RSI unavailable"
    if rsi_val < 30:
        return 2, f"RSI {rsi_val:.1f} — Oversold, strong reversal candidate"
    if rsi_val < 40:
        return 1, f"RSI {rsi_val:.1f} — Approaching oversold, possible bounce"
    if rsi_val > 70:
        return -2, f"RSI {rsi_val:.1f} — Overbought, pullback likely"
    if rsi_val > 60:
        return -1, f"RSI {rsi_val:.1f} — Approaching overbought"
    return 0, f"RSI {rsi_val:.1f} — Neutral"


def _macd_signal(macd_val: float | None, signal_val: float | None, hist: float | None) -> tuple[int, str]:
    if macd_val is None or signal_val is None:
        return 0, "MACD unavailable"
    if hist is not None and hist > 0 and macd_val > signal_val:
        return 1, f"MACD bullish — histogram positive ({hist:+.4f})"
    if hist is not None and hist < 0 and macd_val < signal_val:
        return -1, f"MACD bearish — histogram negative ({hist:+.4f})"
    return 0, f"MACD neutral — line near signal"


def _trend_signal(price: float, sma20: float | None, sma50: float | None) -> tuple[int, str]:
    if sma20 is None or sma50 is None:
        return 0, "Trend data insufficient"
    if price > sma20 > sma50:
        return 2, f"Strong uptrend — price ${price} > SMA20 ${sma20} > SMA50 ${sma50}"
    if price > sma20:
        return 1, f"Uptrend — price above SMA20 (${sma20})"
    if price < sma20 < sma50:
        return -2, f"Strong downtrend — price ${price} < SMA20 ${sma20} < SMA50 ${sma50}"
    if price < sma20:
        return -1, f"Downtrend — price below SMA20 (${sma20})"
    return 0, f"Price at SMA20 (${sma20})"


def _weekly_momentum(weekly_change: float | None) -> tuple[int, str]:
    if weekly_change is None:
        return 0, "5-day data unavailable"
    if weekly_change > 3:
        return 2, f"Strong 5-day gain +{weekly_change:.2f}%"
    if weekly_change > 1:
        return 1, f"5-day gain +{weekly_change:.2f}%"
    if weekly_change < -3:
        return -2, f"Sharp 5-day drop {weekly_change:.2f}%"
    if weekly_change < -1:
        return -1, f"5-day decline {weekly_change:.2f}%"
    return 0, f"Flat 5 days ({weekly_change:+.2f}%)"


def _volume_signal(volume: int | None, avg_vol: int | None, weekly_change: float | None) -> tuple[int, str]:
    if volume is None or avg_vol is None or avg_vol == 0:
        return 0, "Volume data unavailable"
    ratio = volume / avg_vol
    if weekly_change is not None and weekly_change > 0 and ratio > 1.3:
        return 1, f"High volume ({ratio:.1f}x avg) on up move — conviction"
    if weekly_change is not None and weekly_change < 0 and ratio > 1.3:
        return -1, f"High volume ({ratio:.1f}x avg) on down move — distribution"
    return 0, f"Volume {ratio:.1f}x average"


LABELS = [
    (6, 10, "Strong Buy", "strong-buy", "#00d46a"),
    (3, 5, "Buy", "buy", "#3fb950"),
    (-2, 2, "Hold", "hold", "#e3b341"),
    (-5, -3, "Sell", "sell", "#f85149"),
    (-10, -6, "Strong Sell", "strong-sell", "#da3633"),
]


def score_label(score: int) -> tuple[str, str, str]:
    for lo, hi, label, css, color in LABELS:
        if lo <= score <= hi:
            return label, css, color
    return "Hold", "hold", "#e3b341"


def calculate_signal(indicators: dict, weekly: dict | None) -> dict:
    weekly_change = None
    if weekly:
        weekly_change = round((weekly["close"] - weekly["open"]) / weekly["open"] * 100, 2)

    s_rsi, r_rsi = _rsi_signal(indicators.get("rsi"))
    s_macd, r_macd = _macd_signal(
        indicators.get("macd"), indicators.get("macd_signal"), indicators.get("macd_hist")
    )
    s_trend, r_trend = _trend_signal(
        indicators["price"], indicators.get("sma_20"), indicators.get("sma_50")
    )
    s_mom, r_mom = _weekly_momentum(weekly_change)
    s_vol, r_vol = _volume_signal(
        weekly.get("avg_daily_volume") if weekly else None,
        indicators.get("avg_volume_20"),
        weekly_change,
    )

    score = s_rsi + s_macd + s_trend + s_mom + s_vol
    label, css_class, color = score_label(score)

    details = [
        {"name": "RSI (14)", "signal": s_rsi, "reason": r_rsi},
        {"name": "MACD", "signal": s_macd, "reason": r_macd},
        {"name": "Trend (SMA 20/50)", "signal": s_trend, "reason": r_trend},
        {"name": "5-Day Momentum", "signal": s_mom, "reason": r_mom},
        {"name": "Volume", "signal": s_vol, "reason": r_vol},
    ]

    bullish = [d["reason"] for d in details if d["signal"] > 0]
    bearish = [d["reason"] for d in details if d["signal"] < 0]
    neutral = [d["reason"] for d in details if d["signal"] == 0]

    return {
        "score": score,
        "label": label,
        "css_class": css_class,
        "color": color,
        "indicators": details,
        "bullish_reasons": bullish,
        "bearish_reasons": bearish,
        "neutral_reasons": neutral,
        "weekly_change_pct": weekly_change,
    }
