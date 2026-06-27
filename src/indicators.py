import pandas as pd
import numpy as np


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()


def last_n_trading_days_ohlcv(df: pd.DataFrame, end_date: str, n: int = 5) -> dict | None:
    """Extract OHLCV for the last N trading days up to end_date."""
    end = pd.Timestamp(end_date)
    subset = df[df.index <= end]
    if len(subset) < n:
        period = subset
    else:
        period = subset.iloc[-n:]
    if period.empty:
        return None
    return {
        "open": float(period["Open"].iloc[0]),
        "high": float(period["High"].max()),
        "low": float(period["Low"].min()),
        "close": float(period["Close"].iloc[-1]),
        "volume": int(period["Volume"].sum()),
        "avg_daily_volume": int(period["Volume"].mean()),
        "trading_days": len(period),
    }


def compute_indicators(df: pd.DataFrame) -> dict:
    """Compute all indicators from daily data. Returns latest values."""
    close = df["Close"]
    volume = df["Volume"]

    rsi_s = rsi(close)
    macd_line, signal_line, hist = macd(close)
    sma_20 = sma(close, 20)
    sma_50 = sma(close, 50)
    avg_vol_20 = volume.rolling(20).mean()

    last = close.iloc[-1]
    prev = close.iloc[-2] if len(close) >= 2 else last

    return {
        "price": round(float(last), 2),
        "prev_close": round(float(prev), 2),
        "daily_change_pct": round((last - prev) / prev * 100, 2),
        "rsi": round(float(rsi_s.iloc[-1]), 2) if not rsi_s.empty else None,
        "macd": round(float(macd_line.iloc[-1]), 4) if not macd_line.empty else None,
        "macd_signal": round(float(signal_line.iloc[-1]), 4) if not signal_line.empty else None,
        "macd_hist": round(float(hist.iloc[-1]), 4) if not hist.empty else None,
        "sma_20": round(float(sma_20.iloc[-1]), 2) if not sma_20.isna().all() else None,
        "sma_50": round(float(sma_50.iloc[-1]), 2) if not sma_50.isna().all() else None,
        "volume": int(volume.iloc[-1]),
        "avg_volume_20": int(avg_vol_20.iloc[-1]) if not avg_vol_20.isna().all() else None,
    }
