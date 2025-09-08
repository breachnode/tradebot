import argparse
import pandas as pd
from ..common.db import get_conn
from ..analyzer.featuregen import add_features
from ..logic.momentum_vwap import MomentumVWAP


def run(symbol: str) -> dict:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT ts, open, high, low, close, volume FROM ohlc WHERE symbol=? ORDER BY ts ASC",
            conn,
            params=(symbol,),
        )
    if df.empty:
        return {"trades": 0, "pnl": 0.0}
    df.set_index(pd.to_datetime(df["ts"], unit="s"), inplace=True)
    df = add_features(df)
    strat = MomentumVWAP(tp_pct=0.3, sl_pct=0.3)
    cash = 0.0
    in_pos = False
    entry_price = 0.0
    trades = 0
    for _, row in df.iterrows():
        if not in_pos:
            sig = strat.decide_entry(row)
            if sig:
                in_pos = True
                entry_price = row["close"]
                trades += 1
        else:
            chg = (row["close"] - entry_price) / entry_price
            if chg >= strat.tp:
                cash += strat.tp
                in_pos = False
            elif chg <= -strat.sl:
                cash -= strat.sl
                in_pos = False
    return {"trades": trades, "pnl": round(cash, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    args = ap.parse_args()
    res = run(args.symbol)
    print(res)


if __name__ == "__main__":
    main()

