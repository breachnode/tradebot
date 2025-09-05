from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time
import math

from .tradier import TradierClient
from .sources import fetch_yahoo_last_price, fetch_stocktwits_sentiment_score


@dataclass
class Position:
    direction: str  # "call" or "put"
    entry_price: float
    underlying_at_entry: float
    occ_symbol: str
    quantity: int


@dataclass
class RunStats:
    realized_pnl: float = 0.0
    num_wins: int = 0
    num_losses: int = 0
    entries: int = 0


class PaperRunner:
    def __init__(
        self,
        client: TradierClient,
        symbol: str,
        account_id: Optional[str],
        duration_minutes: int = 30,
        poll_seconds: int = 60,
        tp_pct: float = 0.25,
        sl_pct: float = 0.20,
    ):
        self.client = client
        self.symbol = symbol
        self.account_id = account_id
        self.duration_minutes = duration_minutes
        self.poll_seconds = poll_seconds
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.position: Optional[Position] = None
        self.stats = RunStats()

    def _select_near_expiry_occ(self, direction: str) -> Optional[str]:
        exps = self.client.get_options_expirations(self.symbol)
        dates = exps.get("expirations", {}).get("date", [])
        if isinstance(dates, str):
            dates = [dates]
        if not dates:
            return None
        expiry = dates[0]
        chain = self.client.get_options_chain(self.symbol, expiry, greeks=True)
        options = chain.get("options", {}).get("option", [])
        if not options:
            return None
        # Choose delta close to 0.30 for calls or puts
        target_delta = 0.30
        best = None
        best_diff = 1e9
        for o in options:
            greeks = o.get("greeks") or {}
            delta = greeks.get("delta")
            if delta is None:
                continue
            if direction == "call" and delta <= 0:
                continue
            if direction == "put" and delta >= 0:
                continue
            diff = abs(abs(delta) - target_delta)
            if diff < best_diff:
                best = o
                best_diff = diff
        if not best:
            best = options[0]
        return best.get("symbol") or best.get("option_symbol")

    def _estimate_option_price(self, direction: str, underlying_now: float, underlying_entry: float, entry_price: float) -> float:
        # Very rough: option move ~= delta * underlying move
        # Use |delta| ~ 0.30 and ignore decay/vega for a short run
        approx_delta = 0.30
        move = (underlying_now - underlying_entry)
        if direction == "put":
            move = -move
        est = entry_price + approx_delta * move
        return max(est, 0.01)

    def _maybe_enter(self, price_now: float, sentiment_score: int):
        if self.position is not None:
            return
        # Simple rule: bullish sentiment -> call, bearish -> put, otherwise no trade
        if sentiment_score >= 2:
            direction = "call"
        elif sentiment_score <= -2:
            direction = "put"
        else:
            return
        occ = self._select_near_expiry_occ(direction)
        if not occ:
            return
        # Simulate entry at $1.00 premium
        entry_price = 1.00
        self.position = Position(direction=direction, entry_price=entry_price, underlying_at_entry=price_now, occ_symbol=occ, quantity=1)
        self.stats.entries += 1
        print({"enter": {"direction": direction, "occ": occ, "entry_price": entry_price, "underlying": price_now}})

    def _maybe_exit(self, price_now: float):
        if self.position is None:
            return
        pos = self.position
        est_now = self._estimate_option_price(pos.direction, price_now, pos.underlying_at_entry, pos.entry_price)
        change = (est_now - pos.entry_price) / pos.entry_price
        if change >= self.tp_pct or change <= -self.sl_pct:
            pnl = (est_now - pos.entry_price) * pos.quantity * 100.0
            self.stats.realized_pnl += pnl
            if pnl >= 0:
                self.stats.num_wins += 1
            else:
                self.stats.num_losses += 1
            print({"exit": {"pnl": pnl, "est_price": est_now, "underlying": price_now, "reason": "tp" if change>=self.tp_pct else "sl"}})
            self.position = None

    def run(self):
        start = time.time()
        end = start + self.duration_minutes * 60
        while time.time() < end:
            price = fetch_yahoo_last_price(self.symbol) or 0.0
            sent = fetch_stocktwits_sentiment_score(self.symbol)
            print({"tick": {"price": price, "sentiment": sent, "ts": int(time.time())}})
            self._maybe_enter(price, sent)
            self._maybe_exit(price)
            time.sleep(self.poll_seconds)
        # Close any open position at last estimated price
        if self.position is not None:
            pos = self.position
            last_price = fetch_yahoo_last_price(self.symbol) or pos.underlying_at_entry
            est_now = self._estimate_option_price(pos.direction, last_price, pos.underlying_at_entry, pos.entry_price)
            pnl = (est_now - pos.entry_price) * pos.quantity * 100.0
            self.stats.realized_pnl += pnl
            if pnl >= 0:
                self.stats.num_wins += 1
            else:
                self.stats.num_losses += 1
            print({"force_exit": {"pnl": pnl, "est_price": est_now, "underlying": last_price}})
            self.position = None
        print({"summary": {
            "pnl": round(self.stats.realized_pnl, 2),
            "entries": self.stats.entries,
            "wins": self.stats.num_wins,
            "losses": self.stats.num_losses,
        }})

