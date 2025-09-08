import csv
import time
from ..common.db import get_conn


def log_trade(symbol: str, side: str, size: float, entry: float, exit: float, pnl: float, reason: str):
    ts = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO journal(ts, symbol, side, size, entry, exit, pnl, reason) VALUES(?,?,?,?,?,?,?,?)",
            (ts, symbol, side, size, entry, exit, pnl, reason),
        )
        conn.commit()
    with open("journal.csv", "a", newline="") as f:
        csv.writer(f).writerow([ts, symbol, side, size, entry, exit, pnl, reason])

