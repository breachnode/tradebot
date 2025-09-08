import asyncio
import csv
import os
import time
from typing import List

from ..common.settings import SETTINGS
from ..common.db import init_db, get_conn
from ..broker.client import DerivClient


CSV_DIR = "data"


async def stream_symbol(client: DerivClient, symbol: str):
    os.makedirs(CSV_DIR, exist_ok=True)
    csv_path = os.path.join(CSV_DIR, f"ticks_{symbol}.csv")
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        async for msg in client.subscribe_ticks(symbol):
            tick = msg.get("tick") or {}
            epoch = int(tick.get("epoch") or time.time())
            price = float(tick.get("quote") or 0.0)
            with get_conn() as conn:
                conn.execute("INSERT INTO ticks(symbol, epoch, price) VALUES(?,?,?)", (symbol, epoch, price))
                conn.commit()
            writer.writerow([epoch, price])
            f.flush()


async def main():
    init_db()
    client = DerivClient()
    await client.connect_and_auth()
    tasks = [asyncio.create_task(stream_symbol(client, s)) for s in SETTINGS.symbols]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

