"""
Generates deterministic mock OHLCV data for demo mode.
Seeded per symbol+date so each run is consistent.
Real prices are approximate 2025 levels.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

BASE_PRICES = {
    "SOXX": 210.0, "QQQ": 470.0,  "SPY": 555.0,  "RSP": 170.0,
    "NASA": 25.0,  "MTUM": 210.0, "XLV": 148.0,  "XLF": 49.0,
    "XLE":  95.0,  "XLI": 140.0,  "XLY": 215.0,  "XLP": 77.0,
    "XLB":  91.0,  "XLRE": 42.0,  "XLU": 73.0,   "XLC": 102.0,
    # Holdings
    "AVGO": 185.0, "NVDA": 128.0, "AMD": 108.0,  "TXN": 195.0,
    "QCOM": 155.0, "LRCX": 700.0, "KLAC": 630.0, "MRVL": 72.0,
    "MCHP": 70.0,  "ON":   44.0,  "MSFT": 430.0, "AAPL": 210.0,
    "AMZN": 185.0, "META": 570.0, "GOOGL": 170.0,"GOOG": 172.0,
    "TSLA": 250.0, "COST": 900.0, "BRK-B": 460.0,"LLY": 760.0,
    "JPM": 240.0,  "VST":  145.0, "NRG": 100.0,  "PLTR": 85.0,
    "DECK": 130.0, "DAL":  52.0,  "UAL":  68.0,  "HWM":  110.0,
    "PWR":  315.0, "GE":   185.0, "UNH":  540.0, "JNJ":  150.0,
    "ABBV": 190.0, "MRK":  100.0, "PFE":  27.0,  "TMO":  560.0,
    "ABT":  115.0, "DHR":  220.0, "AMGN": 310.0, "V":    285.0,
    "MA":   490.0, "BAC":  44.0,  "WFC":  72.0,  "GS":   530.0,
    "MS":   115.0, "SPGI": 460.0, "SCHW": 78.0,  "XOM":  108.0,
    "CVX":  155.0, "COP":  105.0, "EOG":  125.0, "SLB":  44.0,
    "MPC":  165.0, "VLO":  145.0, "PSX":  125.0, "WMB":  55.0,
    "OKE":  85.0,  "CAT":  350.0, "HON":  205.0, "UNP":  240.0,
    "RTX":  125.0, "DE":   395.0, "LMT":  465.0, "ETN":  310.0,
    "ITW":  260.0, "GD":   270.0, "HD":   370.0, "MCD":  295.0,
    "BKNG": 4800.0,"LOW":  235.0, "TJX":  115.0, "NKE":  75.0,
    "SBUX": 90.0,  "ROST": 145.0, "PG":   165.0, "WMT":  95.0,
    "KO":   65.0,  "PEP":  150.0, "PM":   125.0, "MDLZ": 65.0,
    "MO":   44.0,  "CL":   105.0, "GIS":  65.0,  "LIN":  455.0,
    "SHW":  325.0, "APD":  290.0, "FCX":  45.0,  "ECL":  230.0,
    "NUE":  135.0, "NEM":  47.0,  "PPG":  130.0, "CTVA": 52.0,
    "VMC":  270.0, "AMT":  200.0, "PLD":  120.0, "EQIX": 825.0,
    "CCI":  100.0, "PSA":  310.0, "DLR":  155.0, "SPG":  175.0,
    "WELL": 115.0, "SBAC": 220.0, "CBRE": 120.0, "NEE":  72.0,
    "SO":   88.0,  "DUK":  115.0, "AEP":  100.0, "SRE":  68.0,
    "XEL":  65.0,  "EXC":  42.0,  "ED":   96.0,  "D":    44.0,
    "WEC":  88.0,  "NFLX": 630.0, "TMUS": 215.0, "CMCSA": 41.0,
    "DIS":  100.0, "VZ":   42.0,  "T":    23.0,  "EA":   135.0,
    # Space placeholders
    "BA":   175.0, "NOC":  490.0, "SPCE": 3.0,   "MAXR": 5.0,
    "MNTS": 2.0,   "RKLB": 18.0,  "ASTS": 22.0,  "SATL": 4.0,
    "^VIX": 18.5,
}


def _seed(symbol: str, date_str: str) -> int:
    return abs(hash(symbol + date_str)) % (2**31)


def generate_ohlcv(symbol: str, date_str: str, n_days: int = 65) -> pd.DataFrame:
    np.random.seed(_seed(symbol, date_str))
    base = BASE_PRICES.get(symbol, 100.0)

    daily_vol = base * 0.015
    returns   = np.random.normal(0.0003, daily_vol / base, n_days)
    closes    = base * np.cumprod(1 + returns)
    closes    = np.maximum(closes, base * 0.5)

    end_date = datetime.strptime(date_str, "%Y-%m-%d")
    dates = []
    d = end_date - timedelta(days=n_days * 2)
    while len(dates) < n_days:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    dates = dates[:n_days]

    highs  = closes * np.random.uniform(1.002, 1.025, n_days)
    lows   = closes * np.random.uniform(0.975, 0.998, n_days)
    opens  = lows   + (highs - lows) * np.random.uniform(0.2, 0.8, n_days)
    avg_vol= max(1_000_000, base * 500_000 / 100)
    vols   = np.random.lognormal(np.log(avg_vol), 0.4, n_days).astype(int)

    df = pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols,
    }, index=pd.DatetimeIndex(dates))
    return df


def generate_intraday(symbol: str, date_str: str) -> pd.DataFrame:
    np.random.seed(_seed(symbol, date_str + "_intra"))
    base    = BASE_PRICES.get(symbol, 100.0)
    n_hours = 7
    ret     = np.random.normal(0, base * 0.004 / n_hours, n_hours)
    closes  = base * np.cumprod(1 + ret / base)
    highs   = closes * np.random.uniform(1.001, 1.008, n_hours)
    lows    = closes * np.random.uniform(0.992, 0.999, n_hours)
    opens   = lows + (highs - lows) * np.random.uniform(0.2, 0.8, n_hours)
    vol_base= max(100_000, base * 70_000 / 100)
    vols    = np.random.lognormal(np.log(vol_base), 0.3, n_hours).astype(int)

    end_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=16, minute=0)
    times  = [end_dt - timedelta(hours=n_hours - 1 - i) for i in range(n_hours)]
    df = pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols,
    }, index=pd.DatetimeIndex(times))
    return df


def generate_pcr(symbol: str, date_str: str) -> float:
    np.random.seed(_seed(symbol, date_str + "_pcr"))
    return round(float(np.random.uniform(0.55, 1.25)), 3)


def generate_vix(date_str: str) -> dict:
    np.random.seed(_seed("^VIX", date_str))
    val    = round(float(np.random.uniform(12.0, 32.0)), 2)
    change = round(float(np.random.uniform(-2.5, 2.5)), 2)
    pct    = round(change / max(val - change, 1) * 100, 2)
    level  = "Low" if val < 15 else ("High" if val > 25 else "Moderate")
    sent   = "Risk-On (Bullish)" if val < 15 else ("Fear (Bearish)" if val > 25 else "Cautious")
    return {"value": val, "change": change, "pct_change": pct,
            "level": level, "sentiment": sent, "mock": True}
