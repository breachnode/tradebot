import asyncio
import pandas as pd
from ..common.settings import SETTINGS
from ..common.db import init_db
from ..common.discord import send as discord_send
from ..analyzer.indicators import ema, rsi, vwap
from ..broker.client import DerivClient
from .risk import RiskState, should_halt


async def run_symbol(symbol: str):
    client = DerivClient()
    await client.connect_and_auth()
    bal = await client.get_balance()
    risk_state = RiskState(start_equity=bal)
    gran = 60  # 1m
    async for msg in client.subscribe_candles(symbol, gran):
        candles = msg.get("candles") or []
        if not candles:
            continue
        df = pd.DataFrame(candles)
        df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, inplace=True)
        df["ema5"] = ema(pd.Series(df["close"].astype(float)), 5)
        df["ema20"] = ema(pd.Series(df["close"].astype(float)), 20)
        df["rsi14"] = rsi(pd.Series(df["close"].astype(float)), 14)
        df["vwap"] = vwap(pd.DataFrame({"close": df["close"].astype(float), "volume": df.get("volume", 1.0)}))
        row = df.iloc[-1]
        if should_halt(bal, risk_state):
            continue
        long_bias = float(row["close"]) > float(row["vwap"]) and float(row["ema5"]) > float(row["ema20"])
        if long_bias:
            prop = await client.propose_risefall(symbol=symbol, duration=60, stake=SETTINGS.position_notional, buy_rise=True)
            pid = (prop.get("proposal") or {}).get("id")
            if pid:
                buy = await client.buy(pid, SETTINGS.position_notional)
                discord_send(f"Bought {symbol} stake {SETTINGS.position_notional}")


async def main():
    init_db()
    tasks = [asyncio.create_task(run_symbol(s)) for s in SETTINGS.symbols]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

