import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from src import mock_data

logger = logging.getLogger(__name__)

FORCE_MOCK = False


def _is_mock_forced() -> bool:
    return FORCE_MOCK


class DataFetcher:
    def __init__(self):
        self._network_ok: bool | None = None

    def _check_network(self) -> bool:
        if self._network_ok is not None:
            return self._network_ok
        try:
            import urllib.request
            urllib.request.urlopen("https://finance.yahoo.com", timeout=4)
            self._network_ok = True
        except Exception:
            self._network_ok = False
            logger.warning("No network access — switching to mock data mode")
        return self._network_ok

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def fetch_ohlcv(self, symbol: str, period: str = "3mo", interval: str = "1d", date: str | None = None) -> pd.DataFrame:
        if _is_mock_forced() or not self._check_network():
            return mock_data.generate_ohlcv(symbol, date or self._today())
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                raise ValueError(f"No data for {symbol}")
            df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
            return df
        except Exception as e:
            logger.warning(f"fetch_ohlcv {symbol} live failed ({e}), using mock")
            return mock_data.generate_ohlcv(symbol, self._today())

    def fetch_intraday(self, symbol: str, date: str | None = None) -> pd.DataFrame:
        if _is_mock_forced() or not self._check_network():
            return mock_data.generate_intraday(symbol, date or self._today())
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="5d", interval="1h")
            if df.empty:
                raise ValueError(f"No intraday data for {symbol}")
            df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
            today = df.index.normalize().max()
            df_today = df[df.index.normalize() == today]
            if df_today.empty:
                df_today = df[df.index.normalize() == df.index.normalize().unique()[-1]]
            return df_today
        except Exception as e:
            logger.warning(f"fetch_intraday {symbol} ({e}), using mock")
            return mock_data.generate_intraday(symbol, self._today())

    def fetch_pcr(self, symbol: str, date: str | None = None) -> float | None:
        if _is_mock_forced() or not self._check_network():
            return mock_data.generate_pcr(symbol, date or self._today())
        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                return None
            total_put_oi = 0
            total_call_oi = 0
            for exp in expirations[:3]:
                chain = ticker.option_chain(exp)
                total_put_oi  += chain.puts["openInterest"].sum()
                total_call_oi += chain.calls["openInterest"].sum()
            if total_call_oi == 0:
                return None
            return round(total_put_oi / total_call_oi, 3)
        except Exception as e:
            logger.warning(f"fetch_pcr {symbol} ({e}), using mock")
            return mock_data.generate_pcr(symbol, self._today())

    def fetch_vix(self) -> dict:
        if _is_mock_forced() or not self._check_network():
            return mock_data.generate_vix(self._today())
        try:
            ticker = yf.Ticker("^VIX")
            df = ticker.history(period="5d", interval="1d")
            if df.empty:
                raise ValueError("No VIX data")
            df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
            last  = df.iloc[-1]
            prev  = df.iloc[-2] if len(df) >= 2 else last
            value = round(float(last["Close"]), 2)
            change= round(float(last["Close"] - prev["Close"]), 2)
            pct   = round(float((last["Close"] - prev["Close"]) / prev["Close"] * 100), 2)
            level = "Low" if value < 15 else ("High" if value > 25 else "Moderate")
            sent  = "Risk-On (Bullish)" if value < 15 else ("Fear (Bearish)" if value > 25 else "Cautious")
            return {"value": value, "change": change, "pct_change": pct,
                    "level": level, "sentiment": sent, "mock": False}
        except Exception as e:
            logger.warning(f"fetch_vix ({e}), using mock")
            return mock_data.generate_vix(self._today())
