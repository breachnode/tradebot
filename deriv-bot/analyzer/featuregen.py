import pandas as pd
from .indicators import ema, rsi, vwap


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema5"] = ema(out["close"], 5)
    out["ema20"] = ema(out["close"], 20)
    out["rsi14"] = rsi(out["close"], 14)
    out["vwap"] = vwap(out)
    return out

