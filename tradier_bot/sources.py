from __future__ import annotations
from typing import Dict, Any, Optional
import time
import requests
import yfinance as yf


def fetch_yahoo_last_price(symbol: str) -> Optional[float]:
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1d", interval="1m")
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[-1])
    except Exception:
        return None


def fetch_stocktwits_sentiment_score(symbol: str, *, max_msgs: int = 50) -> int:
    # Approximate sentiment: +1 bullish, -1 bearish, 0 unknown
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return 0
        data = r.json()
        msgs = data.get("messages", [])[:max_msgs]
        score = 0
        for m in msgs:
            sent = (m.get("entities", {}) or {}).get("sentiment") or {}
            if not sent:
                continue
            basic = sent.get("basic")
            if basic == "Bullish":
                score += 1
            elif basic == "Bearish":
                score -= 1
        return score
    except Exception:
        return 0

