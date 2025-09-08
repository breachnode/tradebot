import time
import pandas as pd
from ..common.db import get_conn, init_db
from ..common.settings import SETTINGS


def build_once(symbol: str):
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT epoch, price FROM ticks WHERE symbol=? ORDER BY epoch ASC",
            conn,
            params=(symbol,),
        )
    if df.empty:
        return 0
    df["ts"] = pd.to_datetime(df["epoch"], unit="s")
    df.set_index("ts", inplace=True)
    interval = SETTINGS.ohlc_interval
    rule = "1T" if interval.endswith("m") else "1S"
    ohlc = df["price"].resample(rule).agg(["first", "max", "min", "last", "count"]) \ 
        .rename(columns={"first": "open", "max": "high", "min": "low", "last": "close", "count": "volume"})
    ohlc = ohlc.dropna()
    rows = 0
    with get_conn() as conn:
        for ts, row in ohlc.iterrows():
            ts_i = int(ts.timestamp())
            conn.execute(
                "INSERT OR REPLACE INTO ohlc(symbol, ts, open, high, low, close, volume) VALUES(?,?,?,?,?,?,?)",
                (symbol, ts_i, float(row.open), float(row.high), float(row.low), float(row.close), float(row.volume)),
            )
            rows += 1
        conn.commit()
    return rows


def main():
    init_db()
    symbols = SETTINGS.symbols
    while True:
        total = 0
        for s in symbols:
            total += build_once(s)
        time.sleep(5)


if __name__ == "__main__":
    main()

