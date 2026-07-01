import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE_PRICES = {
    "XLK": 230.0, "XLV": 148.0, "XLF": 49.0, "XLE": 95.0,
    "XLI": 140.0, "XLY": 215.0, "XLP": 77.0, "XLB": 91.0,
    "XLRE": 42.0, "XLU": 73.0, "XLC": 102.0,
    "DRAM": 35.0, "SOXX": 240.0, "EWY": 68.0, "IWM": 210.0,
    "EWT": 55.0, "EWJ": 72.0, "NASA": 28.0,
    "PEJ": 48.0, "CIBR": 58.0, "GRID": 105.0, "QTUM": 75.0,
    "URA": 30.0, "ITA": 150.0, "THRO": 28.0,
    "IGV": 95.0, "CHPY": 22.0,
}


def _seed(symbol: str, date_str: str) -> int:
    return abs(hash(symbol + date_str)) % (2**31)


def _generate_mock_daily(symbol: str, end_date: str, n_days: int = 120) -> pd.DataFrame:
    np.random.seed(_seed(symbol, end_date))
    base = BASE_PRICES.get(symbol, 100.0)
    vol = base * 0.012
    returns = np.random.normal(0.0003, vol / base, n_days)
    closes = base * np.cumprod(1 + returns)
    closes = np.maximum(closes, base * 0.6)

    end = datetime.strptime(end_date, "%Y-%m-%d")
    # Build trading days ending at end_date
    all_dates = []
    d = end
    while len(all_dates) < n_days:
        if d.weekday() < 5:
            all_dates.append(d)
        d -= timedelta(days=1)
    dates = list(reversed(all_dates))

    highs = closes * np.random.uniform(1.002, 1.02, n_days)
    lows = closes * np.random.uniform(0.98, 0.998, n_days)
    opens = lows + (highs - lows) * np.random.uniform(0.25, 0.75, n_days)
    avg_vol = max(5_000_000, base * 800_000 / 100)
    vols = np.random.lognormal(np.log(avg_vol), 0.35, n_days).astype(int)

    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols},
        index=pd.DatetimeIndex(dates[:n_days]),
    )


class DataProvider:
    def __init__(self):
        self._live: bool | None = None

    def is_live(self) -> bool:
        if self._live is not None:
            return self._live
        try:
            import yfinance as yf
            df = yf.Ticker("SPY").history(period="5d", interval="1d")
            self._live = not df.empty
        except Exception:
            self._live = False
        if not self._live:
            logger.warning("Yahoo Finance unreachable — using simulated data")
        return self._live

    def fetch_yearly(self, symbol: str) -> pd.DataFrame:
        end_date = datetime.now().strftime("%Y-%m-%d")
        if not self.is_live():
            return _generate_mock_daily(symbol, end_date, n_days=365)
        try:
            import yfinance as yf
            df = yf.Ticker(symbol).history(period="13mo", interval="1d")
            if df.empty:
                raise ValueError(f"No data for {symbol}")
            df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
            return df
        except Exception as e:
            logger.warning(f"Live yearly fetch failed for {symbol}: {e}")
            return _generate_mock_daily(symbol, end_date, n_days=365)

    def fetch_daily(self, symbol: str, end_date: str) -> pd.DataFrame:
        if not self.is_live():
            return _generate_mock_daily(symbol, end_date)
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="6mo", interval="1d")
            if df.empty:
                raise ValueError(f"No data for {symbol}")
            df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
            return df
        except Exception as e:
            logger.warning(f"Live fetch failed for {symbol}: {e}")
            return _generate_mock_daily(symbol, end_date)
