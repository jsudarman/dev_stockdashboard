import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request

from src.config import SECTOR_ETFS, ETF_SYMBOLS
from src.data_provider import DataProvider
from src.indicators import compute_indicators, weekly_ohlcv
from src.signals import calculate_signal
from src import database as db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
provider = DataProvider()


def _previous_week_monday(ref_date: str | None = None) -> str:
    d = datetime.strptime(ref_date, "%Y-%m-%d") if ref_date else datetime.now()
    d -= timedelta(days=d.weekday())  # this Monday
    d -= timedelta(weeks=1)           # last Monday
    return d.strftime("%Y-%m-%d")


def _week_label(monday: str) -> str:
    start = datetime.strptime(monday, "%Y-%m-%d")
    end = start + timedelta(days=4)
    return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"


def _analyze(symbol: str, week_monday: str, force: bool = False) -> dict:
    if not force:
        cached = db.get_signal(week_monday, symbol)
        if cached:
            return cached

    friday = (datetime.strptime(week_monday, "%Y-%m-%d") + timedelta(days=4)).strftime("%Y-%m-%d")
    df = provider.fetch_daily(symbol, friday)
    indicators = compute_indicators(df)
    weekly = weekly_ohlcv(df, week_monday)
    signal = calculate_signal(indicators, weekly)

    result = {
        "symbol": symbol,
        **SECTOR_ETFS[symbol],
        **indicators,
        "weekly": weekly,
        "signal": signal,
    }

    db.save_signal(week_monday, symbol, result)
    return result


@app.route("/")
def index():
    return render_template("index.html", etfs=SECTOR_ETFS)


@app.route("/api/signals")
def api_signals():
    week = request.args.get("week") or _previous_week_monday()
    force = request.args.get("refresh", "false").lower() == "true"

    results = {}
    for sym in ETF_SYMBOLS:
        try:
            results[sym] = _analyze(sym, week, force)
        except Exception as e:
            logging.error(f"Error analyzing {sym}: {e}")
            results[sym] = {"symbol": sym, "error": str(e), **SECTOR_ETFS[sym]}

    prev_week = _previous_week_monday(week)

    return jsonify({
        "week": week,
        "week_label": _week_label(week),
        "prev_week": prev_week,
        "signals": results,
        "is_mock": not provider.is_live(),
    })


@app.context_processor
def inject_globals():
    return {"is_demo_mode": not provider.is_live()}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
