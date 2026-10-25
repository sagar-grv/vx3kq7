"""SQLite storage for Elexon wind actuals (FUELHH) and forecasts (WINDFOR)."""
import os
import sqlite3

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "wind.db")


def db_path() -> str:
    return os.environ.get("DB_PATH", DEFAULT_DB_PATH)


def get_conn() -> sqlite3.Connection:
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS actuals (
            start_time TEXT PRIMARY KEY,        -- ISO UTC, half-hourly (FUELHH, fuelType=WIND)
            settlement_date TEXT NOT NULL,
            settlement_period INTEGER NOT NULL,
            generation REAL NOT NULL            -- MW
        );
        CREATE TABLE IF NOT EXISTS forecasts (
            start_time TEXT NOT NULL,           -- ISO UTC, hourly target (WINDFOR)
            publish_time TEXT NOT NULL,         -- ISO UTC, when the forecast was published
            generation REAL NOT NULL,           -- MW
            PRIMARY KEY (start_time, publish_time)
        );
        CREATE INDEX IF NOT EXISTS idx_forecasts_publish ON forecasts (publish_time);
        """
    )
    conn.commit()
