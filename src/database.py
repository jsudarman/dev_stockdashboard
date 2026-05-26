import sqlite3
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
DB_PATH = Path(__file__).parent.parent / "data" / "signals.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_signals (
                date      TEXT NOT NULL,
                symbol    TEXT NOT NULL,
                data      TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (date, symbol)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vix_data (
                date      TEXT PRIMARY KEY,
                data      TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
        """)
        conn.commit()


def save_signal(date: str, symbol: str, data: dict):
    from datetime import datetime
    with _connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO daily_signals (date, symbol, data, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (date, symbol, json.dumps(data), datetime.utcnow().isoformat()))
        conn.commit()


def get_signal(date: str, symbol: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM daily_signals WHERE date=? AND symbol=?", (date, symbol)
        ).fetchone()
    if row:
        return json.loads(row["data"])
    return None


def save_vix(date: str, data: dict):
    from datetime import datetime
    with _connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO vix_data (date, data, fetched_at)
            VALUES (?, ?, ?)
        """, (date, json.dumps(data), datetime.utcnow().isoformat()))
        conn.commit()


def get_vix(date: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT data FROM vix_data WHERE date=?", (date,)).fetchone()
    if row:
        return json.loads(row["data"])
    return None


def list_available_dates() -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM daily_signals ORDER BY date DESC LIMIT 30"
        ).fetchall()
    return [r["date"] for r in rows]
