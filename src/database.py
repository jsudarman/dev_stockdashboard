import sqlite3
import json
import logging
from datetime import datetime
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
            CREATE TABLE IF NOT EXISTS weekly_signals (
                week_start TEXT NOT NULL,
                symbol     TEXT NOT NULL,
                data       TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (week_start, symbol)
            )
        """)
        conn.commit()


def save_signal(week_start: str, symbol: str, data: dict):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO weekly_signals VALUES (?, ?, ?, ?)",
            (week_start, symbol, json.dumps(data), datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_signal(week_start: str, symbol: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM weekly_signals WHERE week_start=? AND symbol=?",
            (week_start, symbol),
        ).fetchone()
    return json.loads(row["data"]) if row else None


def list_weeks() -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT week_start FROM weekly_signals ORDER BY week_start DESC LIMIT 20"
        ).fetchall()
    return [r["week_start"] for r in rows]


init_db()
