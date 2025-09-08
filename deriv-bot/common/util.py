import asyncio, json, time


def now_ms() -> int:
    return int(time.time() * 1000)


def to_json(obj) -> str:
    return json.dumps(obj, separators=(",", ":"))


async def sleep_backoff(attempt: int, base: float = 0.5, cap: float = 10.0):
    await asyncio.sleep(min(cap, base * (2 ** attempt)))

