import sqlite3
from contextlib import contextmanager


DB_PATH = "data.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS ticks(symbol TEXT, epoch INTEGER, price REAL)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS ohlc(symbol TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS journal(ts INTEGER, symbol TEXT, side TEXT, size REAL, entry REAL, exit REAL, pnl REAL, reason TEXT)"
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

