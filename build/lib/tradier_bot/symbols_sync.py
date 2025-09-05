from __future__ import annotations
from typing import List, Tuple
import time

from .tradier import TradierClient


def _normalize_symbols(raw: str) -> List[str]:
    parts = raw.replace("\n", ",").split(",")
    return [p.strip().upper() for p in parts if p.strip()]


def load_symbols_from_file(path: str) -> List[str]:
    with open(path, "r") as f:
        content = f.read()
    syms = _normalize_symbols(content)
    # preserve order but dedupe
    return list(dict.fromkeys(syms))


def cross_reference_optionable(
    client: TradierClient,
    symbols: List[str],
    *,
    limit: int | None = None,
    sleep_seconds: float = 0.3,
) -> Tuple[List[str], List[str]]:
    optionable: List[str] = []
    not_optionable: List[str] = []
    count = 0
    for sym in symbols:
        if limit is not None and count >= limit:
            break
        try:
            exps = client.get_options_expirations(sym)
            dates = (exps.get("expirations") or {}).get("date")
            if dates:
                optionable.append(sym)
            else:
                not_optionable.append(sym)
        except Exception:
            not_optionable.append(sym)
        count += 1
        time.sleep(sleep_seconds)
    return optionable, not_optionable

