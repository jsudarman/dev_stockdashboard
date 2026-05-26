import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def calc_vwap(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    try:
        tp = (df["High"] + df["Low"] + df["Close"]) / 3
        cum_vol = df["Volume"].cumsum()
        cum_tp_vol = (tp * df["Volume"]).cumsum()
        vwap_series = cum_tp_vol / cum_vol.replace(0, np.nan)
        return float(vwap_series.iloc[-1])
    except Exception:
        return None


def calc_cmf(high: pd.Series, low: pd.Series, close: pd.Series,
             volume: pd.Series, period: int = 20) -> pd.Series:
    hl_range = (high - low).replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / hl_range
    mfv = mfm * volume
    return mfv.rolling(period).sum() / volume.rolling(period).sum().replace(0, np.nan)


def calc_mfi(high: pd.Series, low: pd.Series, close: pd.Series,
             volume: pd.Series, period: int = 14) -> pd.Series:
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    pos_mf = raw_mf.where(tp > tp.shift(1), 0)
    neg_mf = raw_mf.where(tp < tp.shift(1), 0)
    pos_sum = pos_mf.rolling(period).sum()
    neg_sum = neg_mf.rolling(period).sum().replace(0, np.nan)
    mfr = pos_sum / neg_sum
    return 100 - (100 / (1 + mfr))


def detect_mfi_divergence(close: pd.Series, mfi: pd.Series, lookback: int = 10) -> int:
    if len(close) < lookback + 2:
        return 0
    recent_close = close.iloc[-lookback:]
    recent_mfi = mfi.iloc[-lookback:]
    if recent_close.isna().all() or recent_mfi.isna().all():
        return 0

    price_low_idx = recent_close.idxmin()
    prev_close = close.iloc[-(lookback + 5):-lookback]
    prev_mfi = mfi.iloc[-(lookback + 5):-lookback]

    if prev_close.empty or prev_mfi.empty:
        return 0

    prev_low = prev_close.min()
    prev_mfi_at_low = prev_mfi.min()
    curr_low = recent_close.min()
    curr_mfi_at_low = recent_mfi.min()

    if curr_low < prev_low and curr_mfi_at_low > prev_mfi_at_low:
        return 1

    prev_high = prev_close.max()
    prev_mfi_at_high = prev_mfi.max()
    curr_high = recent_close.max()
    curr_mfi_at_high = recent_mfi.max()

    if curr_high > prev_high and curr_mfi_at_high < prev_mfi_at_high:
        return -1

    return 0


def compute_all(df_daily: pd.DataFrame, df_intraday: pd.DataFrame, pcr: float | None) -> dict:
    high   = df_daily["High"]
    low    = df_daily["Low"]
    close  = df_daily["Close"]
    volume = df_daily["Volume"]
    open_  = df_daily["Open"]

    rsi_series  = calc_rsi(close)
    ema9_series = calc_ema(close, 9)
    ema20_series= calc_ema(close, 20)
    cmf_series  = calc_cmf(high, low, close, volume)
    mfi_series  = calc_mfi(high, low, close, volume)
    vwap_val    = calc_vwap(df_intraday)
    div_signal  = detect_mfi_divergence(close, mfi_series)

    last_close  = float(close.iloc[-1])
    last_open   = float(open_.iloc[-1])
    last_vol    = float(volume.iloc[-1])
    avg_vol     = float(volume.rolling(20).mean().iloc[-1]) if len(volume) >= 20 else float(volume.mean())

    rsi_val  = float(rsi_series.iloc[-1])  if not rsi_series.empty  else None
    ema9_val = float(ema9_series.iloc[-1]) if not ema9_series.empty else None
    ema20_val= float(ema20_series.iloc[-1])if not ema20_series.empty else None
    cmf_val  = float(cmf_series.iloc[-1]) if not cmf_series.empty  else None
    mfi_val  = float(mfi_series.iloc[-1]) if not mfi_series.empty  else None

    vol_ratio = round(last_vol / avg_vol, 2) if avg_vol else None
    prev_close  = float(close.iloc[-2]) if len(close) >= 2 else last_close
    price_change_pct = round((last_close - prev_close) / prev_close * 100, 2)

    return {
        "close":         round(last_close, 2),
        "open":          round(last_open, 2),
        "price_change_pct": price_change_pct,
        "rsi":           round(rsi_val,  2) if rsi_val  is not None else None,
        "ema9":          round(ema9_val, 2) if ema9_val is not None else None,
        "ema20":         round(ema20_val,2) if ema20_val is not None else None,
        "vwap":          round(vwap_val, 2) if vwap_val is not None else None,
        "volume":        int(last_vol),
        "avg_volume":    int(avg_vol),
        "vol_ratio":     vol_ratio,
        "pcr":           pcr,
        "cmf":           round(cmf_val,  4) if cmf_val  is not None else None,
        "mfi":           round(mfi_val,  2) if mfi_val  is not None else None,
        "mfi_divergence":div_signal,
    }
