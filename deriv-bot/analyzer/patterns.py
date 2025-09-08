import pandas as pd


def breakout(df: pd.DataFrame) -> pd.Series:
    return (df["close"] > df["vwap"]) & (df["ema5"] > df["ema20"])  # boolean


def mean_revert(df: pd.DataFrame) -> pd.Series:
    return (df["rsi14"] < 30) | (df["rsi14"] > 70)

