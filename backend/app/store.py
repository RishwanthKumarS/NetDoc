"""
Keeps a rolling history of telemetry so the dashboard can draw a
signal-over-time chart per device. SQLite is overkill for what's
basically a ring buffer, but it means the history survives a backend
restart during the demo, which an in-memory list wouldn't.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "telemetry_history.db"
HISTORY_WINDOW_SECONDS = 30 * 60  # keep the last 30 minutes per device


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_history (
            device_id TEXT NOT NULL,
            timestamp REAL NOT NULL,
            rssi_dbm REAL NOT NULL,
            snr_db REAL NOT NULL,
            link_rate_mbps REAL NOT NULL,
            diagnostic_code TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_device_time ON telemetry_history(device_id, timestamp)"
    )
    return conn


def record_sample(conn: sqlite3.Connection, device_id: str, rssi_dbm: float, snr_db: float,
                   link_rate_mbps: float, diagnostic_code: str) -> None:
    conn.execute(
        "INSERT INTO telemetry_history VALUES (?, ?, ?, ?, ?, ?)",
        (device_id, time.time(), rssi_dbm, snr_db, link_rate_mbps, diagnostic_code),
    )
    conn.commit()


def prune_old_samples(conn: sqlite3.Connection) -> None:
    cutoff = time.time() - HISTORY_WINDOW_SECONDS
    conn.execute("DELETE FROM telemetry_history WHERE timestamp < ?", (cutoff,))
    conn.commit()


def get_history(conn: sqlite3.Connection, device_id: str, limit: int = 200) -> list[dict]:
    rows = conn.execute(
        """
        SELECT timestamp, rssi_dbm, snr_db, link_rate_mbps, diagnostic_code
        FROM telemetry_history
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (device_id, limit),
    ).fetchall()
    rows.reverse()
    return [
        {
            "timestamp": r[0],
            "rssi_dbm": r[1],
            "snr_db": r[2],
            "link_rate_mbps": r[3],
            "diagnostic_code": r[4],
        }
        for r in rows
    ]
