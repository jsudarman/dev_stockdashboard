import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request

from src.config import SECTOR_ETFS, ETF_SYMBOLS
from src.data_provider import DataProvider
from src.indicators import compute_indicators, last_n_trading_days_ohlcv
from src.signals import calculate_signal
from src import database as db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
provider = DataProvider()


def _end_date(ref_date: str | None = None) -> str:
    d = datetime.strptime(ref_date, "%Y-%m-%d") if ref_date else datetime.now()
    return d.strftime("%Y-%m-%d")


def _period_label(end_date: str) -> str:
    end = datetime.strptime(end_date, "%Y-%m-%d")
    start = end - timedelta(days=6)
    return f"5 trading days ending {end.strftime('%b %d, %Y')}"


def _analyze(symbol: str, end_date: str, force: bool = False) -> dict:
    if not force:
        cached = db.get_signal(end_date, symbol)
        if cached:
            return cached

    df = provider.fetch_daily(symbol, end_date)
    indicators = compute_indicators(df)
    period_data = last_n_trading_days_ohlcv(df, end_date, n=5)
    signal = calculate_signal(indicators, period_data)

    result = {
        "symbol": symbol,
        **SECTOR_ETFS[symbol],
        **indicators,
        "weekly": period_data,
        "signal": signal,
    }

    db.save_signal(end_date, symbol, result)
    return result


@app.route("/")
def index():
    return render_template("index.html", etfs=SECTOR_ETFS)


@app.route("/api/signals")
def api_signals():
    end = request.args.get("end_date") or _end_date()
    force = request.args.get("refresh", "false").lower() == "true"

    results = {}
    for sym in ETF_SYMBOLS:
        try:
            results[sym] = _analyze(sym, end, force)
        except Exception as e:
            logging.error(f"Error analyzing {sym}: {e}")
            results[sym] = {"symbol": sym, "error": str(e), **SECTOR_ETFS[sym]}

    return jsonify({
        "end_date": end,
        "week_label": _period_label(end),
        "signals": results,
        "is_mock": not provider.is_live(),
    })


@app.context_processor
def inject_globals():
    return {"is_demo_mode": not provider.is_live()}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
