import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request

from src import database as db
from src.data_fetcher import DataFetcher
from src.signals import calculate_signals
from src.etf_info import ETF_INFO, ETF_SYMBOLS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
fetcher = DataFetcher()


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _prev_trading_date(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _next_trading_date(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    today = datetime.now().date()
    if d.date() > today:
        return date_str
    return d.strftime("%Y-%m-%d")


def fetch_and_calc(symbol: str, force: bool, date: str) -> dict:
    if not force:
        cached = db.get_signal(date, symbol)
        if cached:
            cached["from_cache"] = True
            return cached
    try:
        df_daily    = fetcher.fetch_ohlcv(symbol,   date=date)
        df_intraday = fetcher.fetch_intraday(symbol, date=date)
        pcr         = fetcher.fetch_pcr(symbol,      date=date)
        result      = calculate_signals(symbol, df_daily, df_intraday, pcr)
        result["from_cache"] = False
        db.save_signal(date, symbol, result)
        return result
    except Exception as e:
        logger.error(f"fetch_and_calc {symbol}: {e}")
        error_result = {
            "symbol":    symbol,
            "error":     str(e),
            "score":     0,
            "label":     "N/A",
            "css_class": "unavailable",
            "color":     "#888",
        }
        return error_result


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", etf_symbols=ETF_SYMBOLS, etf_info=ETF_INFO)


@app.route("/etf/<symbol>")
def etf_detail(symbol: str):
    symbol = symbol.upper()
    info = ETF_INFO.get(symbol, {"name": symbol, "description": "Unknown ETF", "holdings": []})
    return render_template("etf_detail.html", symbol=symbol, etf_info=ETF_INFO)


@app.route("/api/signals")
def api_signals():
    date    = request.args.get("date", _today())
    refresh = request.args.get("refresh", "false").lower() == "true"

    signals = {}
    for symbol in ETF_SYMBOLS:
        signals[symbol] = fetch_and_calc(symbol, force=refresh, date=date)

    # VIX
    vix = db.get_vix(date) if not refresh else None
    if vix is None:
        try:
            vix = fetcher.fetch_vix()
            db.save_vix(date, vix)
        except Exception as e:
            vix = {"value": None, "error": str(e)}

    is_mock = not fetcher._check_network()
    return jsonify({
        "date":              date,
        "signals":           signals,
        "vix":               vix,
        "available_dates":   db.list_available_dates(),
        "prev_date":         _prev_trading_date(date),
        "next_date":         _next_trading_date(date),
        "is_today":          date == _today(),
        "is_mock":           is_mock,
    })


@app.route("/api/etf/<symbol>")
def api_etf_detail(symbol: str):
    symbol  = symbol.upper()
    date    = request.args.get("date", _today())
    refresh = request.args.get("refresh", "false").lower() == "true"
    info    = ETF_INFO.get(symbol, {})
    holdings = info.get("holdings", [])

    etf_signal = fetch_and_calc(symbol, force=False, date=date)

    holding_signals = {}
    for h in holdings:
        ticker = h["ticker"]
        holding_signals[ticker] = fetch_and_calc(ticker, force=refresh, date=date)

    return jsonify({
        "symbol":          symbol,
        "info":            info,
        "etf_signal":      etf_signal,
        "holding_signals": holding_signals,
        "date":            date,
        "is_mock":         not fetcher._check_network(),
    })


@app.route("/api/dates")
def api_dates():
    return jsonify(db.list_available_dates())


@app.context_processor
def inject_globals():
    return {"is_demo_mode": not fetcher._check_network()}


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
