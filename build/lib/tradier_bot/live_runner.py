from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import time
import math
import statistics

import yfinance as yf

from .tradier import TradierClient
from .sources import fetch_stocktwits_sentiment_score


@dataclass
class LivePosition:
    symbol: str              # underlying
    direction: str           # call | put
    occ_symbol: str          # option OCC symbol
    quantity: int
    entry_price: float       # option premium per contract
    order_id: Optional[str]  # entry order id


class LiveRunner:
    def __init__(
        self,
        client: TradierClient,
        account_id: str,
        symbols: List[str],
        starting_capital: float = 100.0,
        duration_minutes: int = 30,
        poll_seconds: int = 30,
        tp_pct: float = 0.25,
        sl_pct: float = 0.20,
        max_positions: int = 1,
        target_delta: float = 0.30,
        aggressiveness: float = 0.5,
        min_open_interest: int = 50,
        max_spread_abs: float = 0.25,
        max_spread_pct: float = 0.35,
        min_sentiment_score: int = 1,
        reinvestment_rate: float = 0.5,
    ) -> None:
        self.client = client
        self.account_id = account_id
        self.symbols = symbols
        self.cash = starting_capital
        self.duration_minutes = duration_minutes
        self.poll_seconds = poll_seconds
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.max_positions = max_positions
        self.target_delta = target_delta
        self.positions: List[LivePosition] = []
        self.aggressiveness = max(0.0, min(1.0, aggressiveness))
        self.min_open_interest = min_open_interest
        self.max_spread_abs = max_spread_abs
        self.max_spread_pct = max_spread_pct
        self.min_sentiment_score = min_sentiment_score
        self.reinvest = max(0.0, min(1.0, reinvestment_rate))

    # Data helpers
    def _yahoo_prices(self, symbol: str, minutes: int = 20) -> List[float]:
        try:
            t = yf.Ticker(symbol)
            df = t.history(period="1d", interval="1m")
            if df is None or df.empty:
                return []
            closes = [float(x) for x in df["Close"].tolist()]
            return closes[-minutes:]
        except Exception:
            return []

    def _momentum_signal(self, symbol: str) -> Optional[str]:
        closes = self._yahoo_prices(symbol)
        if len(closes) < 10:
            return None
        short = statistics.fmean(closes[-3:])
        long = statistics.fmean(closes[-9:])
        # Lower threshold when aggressiveness is higher
        up_thresh = 1.0 + (0.001 * (1.0 - self.aggressiveness))
        down_thresh = 1.0 - (0.001 * (1.0 - self.aggressiveness))
        if short > long * up_thresh:
            return "call"
        if short < long * down_thresh:
            return "put"
        return None

    def _breakout_signal(self, symbol: str) -> Optional[str]:
        closes = self._yahoo_prices(symbol)
        if len(closes) < 15:
            return None
        last = closes[-1]
        recent_high = max(closes[-15:])
        recent_low = min(closes[-15:])
        # Make breakout easier with higher aggressiveness
        breakout_pad = 0.0005 * (1.0 - self.aggressiveness)
        if last >= recent_high * (1.0 - breakout_pad):
            return "call"
        if last <= recent_low * (1.0 + breakout_pad):
            return "put"
        return None

    def _liquidity_ok(self, occ_symbol: str) -> bool:
        q = self.client.get_quote(occ_symbol)
        quote = (q.get("quotes") or {}).get("quote") or {}
        if isinstance(quote, list) and quote:
            quote = quote[0]
        bid = float(quote.get("bid") or 0.0)
        ask = float(quote.get("ask") or 0.0)
        oi = int(quote.get("open_interest") or 0)
        if ask <= 0.0:
            return False
        spread = ask - bid
        spread_ok = (spread <= self.max_spread_abs) or (spread / ask <= self.max_spread_pct)
        return oi >= self.min_open_interest and spread_ok

    def _pick_option(self, symbol: str, direction: str) -> Optional[str]:
        exps = self.client.get_options_expirations(symbol)
        dates = exps.get("expirations", {}).get("date", [])
        if isinstance(dates, str):
            dates = [dates]
        if not dates:
            return None
        expiry = dates[0]
        chain = self.client.get_options_chain(symbol, expiry, greeks=True)
        options = chain.get("options", {}).get("option", [])
        if not options:
            return None
        # Filter by liquidity first if fields available
        candidates = []
        for o in options:
            g = o.get("greeks") or {}
            d = g.get("delta")
            if d is None:
                continue
            if direction == "call" and d <= 0:
                continue
            if direction == "put" and d >= 0:
                continue
            # Basic quote data in chain
            bid = float(o.get("bid") or 0.0)
            ask = float(o.get("ask") or 0.0)
            oi = int(o.get("open_interest") or 0)
            if ask <= 0.0:
                continue
            spread = ask - bid
            spread_ok = (spread <= self.max_spread_abs) or (spread / ask <= self.max_spread_pct)
            if oi >= self.min_open_interest and spread_ok:
                candidates.append(o)
        pool = candidates if candidates else options
        best = None
        best_diff = 1e9
        for o in pool:
            d = (o.get("greeks") or {}).get("delta")
            if d is None:
                continue
            diff = abs(abs(d) - self.target_delta)
            if diff < best_diff:
                best = o
                best_diff = diff
        if not best:
            best = pool[0]
        return best.get("symbol") or best.get("option_symbol")

    def _option_mid(self, occ_symbol: str) -> Optional[float]:
        q = self.client.get_quote(occ_symbol)
        quote = (q.get("quotes") or {}).get("quote") or {}
        if isinstance(quote, list) and quote:
            quote = quote[0]
        bid = quote.get("bid") or 0.0
        ask = quote.get("ask") or 0.0
        if bid and ask:
            return round((float(bid) + float(ask)) / 2.0, 2)
        last = quote.get("last")
        if last:
            return round(float(last), 2)
        return None

    def _place_buy(self, symbol: str, direction: str) -> Optional[LivePosition]:
        occ = self._pick_option(symbol, direction)
        if not occ:
            return None
        mid = self._option_mid(occ) or 0.01
        price = max(0.01, round(mid, 2))
        cost_per_contract = price * 100.0
        if self.cash < cost_per_contract:
            print({"skip": {"symbol": symbol, "reason": "insufficient_cash", "cash": round(self.cash,2), "needed": cost_per_contract}})
            return None
        # Determine quantity using reinvestment fraction of current cash
        target_allocation = self.cash * self.reinvest
        qty = int(target_allocation // cost_per_contract)
        if qty < 1:
            qty = 1
        spend = qty * cost_per_contract
        if spend > self.cash:
            qty = int(self.cash // cost_per_contract)
            if qty < 1:
                print({"skip": {"symbol": symbol, "reason": "insufficient_cash_after_size", "cash": round(self.cash,2)}})
                return None
            spend = qty * cost_per_contract
        # Preview -> place
        self.client.preview_option_order(
            account_id=self.account_id,
            underlying_symbol=symbol,
            option_symbol=occ,
            side="buy_to_open",
            quantity=qty,
            price=price,
            order_type="limit",
            duration="day",
        )
        placed = self.client.place_option_order(
            account_id=self.account_id,
            underlying_symbol=symbol,
            option_symbol=occ,
            side="buy_to_open",
            quantity=qty,
            price=price,
            order_type="limit",
            duration="day",
        )
        order_id = (placed.get("order") or {}).get("id") or placed.get("id")
        pos = LivePosition(symbol=symbol, direction=direction, occ_symbol=occ, quantity=qty, entry_price=price, order_id=str(order_id) if order_id else None)
        self.cash -= spend
        print({"buy": {"symbol": symbol, "occ": occ, "price": price, "qty": qty, "order_id": order_id, "cash_after": round(self.cash,2)}})
        return pos

    def _try_close(self, pos: LivePosition, reason: str) -> bool:
        # Place a sell_to_close at bid (approximate fill)
        mid = self._option_mid(pos.occ_symbol) or pos.entry_price
        # Bias to get out: use min(mid, entry_price*(1-sl)) for stop or mid for TP
        price = round(mid, 2)
        self.client.preview_option_order(
            account_id=self.account_id,
            underlying_symbol=pos.symbol,
            option_symbol=pos.occ_symbol,
            side="sell_to_close",
            quantity=pos.quantity,
            price=price,
            order_type="limit",
            duration="day",
        )
        placed = self.client.place_option_order(
            account_id=self.account_id,
            underlying_symbol=pos.symbol,
            option_symbol=pos.occ_symbol,
            side="sell_to_close",
            quantity=pos.quantity,
            price=price,
            order_type="limit",
            duration="day",
        )
        order_id = (placed.get("order") or {}).get("id") or placed.get("id")
        proceeds = price * 100.0
        self.cash += proceeds
        print({"sell": {"symbol": pos.symbol, "occ": pos.occ_symbol, "price": price, "order_id": order_id, "reason": reason, "cash_after": round(self.cash,2)}})
        return True

    def _pnl_change(self, pos: LivePosition) -> Optional[float]:
        mid = self._option_mid(pos.occ_symbol)
        if mid is None:
            return None
        return (mid - pos.entry_price) / pos.entry_price

    def run(self) -> None:
        start = time.time()
        end = start + self.duration_minutes * 60
        while time.time() < end:
            # Exit checks first
            for pos in list(self.positions):
                chg = self._pnl_change(pos)
                if chg is None:
                    continue
                if chg >= self.tp_pct:
                    self._try_close(pos, reason="tp")
                    self.positions.remove(pos)
                    continue
                if chg <= -self.sl_pct:
                    self._try_close(pos, reason="sl")
                    self.positions.remove(pos)
                    continue

            # Entry logic if capacity available
            if len(self.positions) < self.max_positions:
                for sym in self.symbols:
                    # Combine signals: momentum + breakout, then sentiment filter
                    mom = self._momentum_signal(sym)
                    brk = self._breakout_signal(sym)
                    signal = mom or brk
                    if not signal:
                        continue
                    sent = fetch_stocktwits_sentiment_score(sym)
                    if abs(sent) < self.min_sentiment_score:
                        continue
                    # Align sentiment sign with direction when possible
                    if (signal == "call" and sent < 0) or (signal == "put" and sent > 0):
                        # if aggressive, allow misalignment occasionally
                        if self.aggressiveness < 0.7:
                            continue
                    pos = self._place_buy(sym, signal)
                    if pos:
                        self.positions.append(pos)
                        break

            print({"tick": {"ts": int(time.time()), "cash": round(self.cash,2), "positions": [p.occ_symbol for p in self.positions]}})
            time.sleep(self.poll_seconds)

        # Close any open positions at end
        for pos in list(self.positions):
            self._try_close(pos, reason="eod")
            self.positions.remove(pos)
        print({"summary": {"ending_cash": round(self.cash,2)}})

