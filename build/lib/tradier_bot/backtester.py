from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import math
import statistics
import datetime as dt

import yfinance as yf


@dataclass
class BtPosition:
    symbol: str
    direction: str  # call | put
    entry_underlying: float
    entry_premium: float
    entry_date: dt.date
    quantity: int = 1


@dataclass
class BtStats:
    starting_capital: float
    ending_cash: float
    realized_pnl: float
    trades: int
    wins: int
    losses: int
    max_drawdown_pct: float
    cagr_pct: float


class Backtester:
    def __init__(
        self,
        symbols: List[str],
        *,
        years: int = 2,
        starting_capital: float = 100.0,
        tp_pct: float = 0.25,
        sl_pct: float = 0.20,
        target_delta: float = 0.30,
        max_positions: int = 1,
        max_hold_days: int = 10,
        aggressiveness: float = 0.6,
    ) -> None:
        self.symbols = symbols
        self.starting_capital = starting_capital
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.target_delta = target_delta
        self.max_positions = max_positions
        self.max_hold_days = max_hold_days
        self.aggressiveness = max(0.0, min(1.0, aggressiveness))

        self.cash = starting_capital
        self.positions: List[BtPosition] = []
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.equity_curve: List[float] = []

        end = dt.date.today()
        start = end - dt.timedelta(days=365 * years + 10)
        self.start_date = start
        self.end_date = end

    def _fetch_history(self, symbol: str):
        df = yf.Ticker(symbol).history(start=self.start_date, end=self.end_date, interval="1d")
        return df

    @staticmethod
    def _sma(values: List[float], n: int) -> Optional[float]:
        if len(values) < n:
            return None
        return statistics.fmean(values[-n:])

    def _signal(self, closes: List[float]) -> Optional[str]:
        if len(closes) < 20:
            return None
        short = self._sma(closes, 3)
        long = self._sma(closes, 9)
        recent_high = max(closes[-20:])
        recent_low = min(closes[-20:])
        last = closes[-1]
        up_thresh = 1.0 + (0.001 * (1.0 - self.aggressiveness))
        down_thresh = 1.0 - (0.001 * (1.0 - self.aggressiveness))
        if short is not None and long is not None:
            if short > long * up_thresh:
                return "call"
            if short < long * down_thresh:
                return "put"
        breakout_pad = 0.0005 * (1.0 - self.aggressiveness)
        if last >= recent_high * (1.0 - breakout_pad):
            return "call"
        if last <= recent_low * (1.0 + breakout_pad):
            return "put"
        return None

    def _estimate_option_price(self, direction: str, underlying_now: float, underlying_entry: float, entry_price: float) -> float:
        approx_delta = self.target_delta
        move = underlying_now - underlying_entry
        if direction == "put":
            move = -move
        est = entry_price + approx_delta * move
        return max(est, 0.01)

    def _update_equity(self, date_idx_prices: Dict[str, float]):
        # Estimate value of open positions at today's close and record equity
        unrealized = 0.0
        for p in self.positions:
            u_now = date_idx_prices.get(p.symbol, p.entry_underlying)
            est = self._estimate_option_price(p.direction, u_now, p.entry_underlying, p.entry_premium)
            unrealized += est * 100.0 * p.quantity
        self.equity_curve.append(self.cash + unrealized)

    def run(self) -> BtStats:
        # Download histories for all symbols
        histories: Dict[str, Any] = {}
        all_dates: List[dt.date] = []
        for s in self.symbols:
            df = self._fetch_history(s)
            if df is None or df.empty:
                continue
            df = df.dropna()
            histories[s] = df
            all_dates.extend([d.date() for d in df.index])
        if not histories:
            return BtStats(self.starting_capital, self.cash, 0.0, 0, 0, 0, 0.0, 0.0)
        # Build sorted unique date index
        all_dates = sorted(set(all_dates))

        # Dict of trailing closes for signals
        trailing: Dict[str, List[float]] = {s: [] for s in histories.keys()}

        for d in all_dates:
            # Build per-day close map
            day_prices: Dict[str, float] = {}
            for s, df in histories.items():
                if d in [idx.date() for idx in df.index]:
                    # get row by date
                    row = df.loc[str(d)]
                    # row may be Series or DataFrame for multi rows
                    close = None
                    if hasattr(row, "__len__") and "Close" in row:
                        # single row Series
                        close = float(row["Close"]) if not hasattr(row["Close"], "iloc") else float(row["Close"].iloc[0])
                    else:
                        try:
                            close = float(df.loc[str(d)]["Close"])  # fallback
                        except Exception:
                            pass
                    if close is not None:
                        trailing[s].append(close)
                        day_prices[s] = close

            # Exit logic first
            remaining_positions: List[BtPosition] = []
            for p in self.positions:
                u_now = day_prices.get(p.symbol, p.entry_underlying)
                est = self._estimate_option_price(p.direction, u_now, p.entry_underlying, p.entry_premium)
                change = (est - p.entry_premium) / p.entry_premium
                days_held = (d - p.entry_date).days
                should_exit = change >= self.tp_pct or change <= -self.sl_pct or days_held >= self.max_hold_days
                if should_exit:
                    pnl = (est - p.entry_premium) * 100.0 * p.quantity
                    self.cash += (p.entry_premium * 100.0 * p.quantity) + pnl
                    self.trades += 1
                    if pnl >= 0:
                        self.wins += 1
                    else:
                        self.losses += 1
                else:
                    remaining_positions.append(p)
            self.positions = remaining_positions

            # Entry logic if capacity
            if len(self.positions) < self.max_positions:
                for s, closes in trailing.items():
                    if s not in day_prices:
                        continue
                    signal = self._signal(closes)
                    if not signal:
                        continue
                    # can we afford one contract at $1.00?
                    cost = 100.0
                    if self.cash >= cost:
                        self.cash -= cost
                        self.positions.append(
                            BtPosition(symbol=s, direction=signal, entry_underlying=closes[-1], entry_premium=1.00, entry_date=d)
                        )
                        # One position per day
                        break

            # Equity update
            self._update_equity(day_prices)

        # Close any open at last price
        if self.positions:
            # Use last available prices in day_prices from last loop
            last_prices = {s: trailing[s][-1] for s in trailing if trailing[s]}
            for p in self.positions:
                u_now = last_prices.get(p.symbol, p.entry_underlying)
                est = self._estimate_option_price(p.direction, u_now, p.entry_underlying, p.entry_premium)
                pnl = (est - p.entry_premium) * 100.0 * p.quantity
                self.cash += (p.entry_premium * 100.0 * p.quantity) + pnl
                self.trades += 1
                if pnl >= 0:
                    self.wins += 1
                else:
                    self.losses += 1
            self.positions.clear()

        # Metrics
        ending_cash = self.cash
        realized_pnl = ending_cash - self.starting_capital
        peak = -1e9
        max_dd = 0.0
        for eq in self.equity_curve:
            peak = max(peak, eq)
            if peak > 0:
                dd = (peak - eq) / peak
                max_dd = max(max_dd, dd)
        years = max(0.0001, (self.end_date - self.start_date).days / 365.0)
        cagr = (ending_cash / self.starting_capital) ** (1.0 / years) - 1.0 if ending_cash > 0 else -1.0
        return BtStats(
            starting_capital=self.starting_capital,
            ending_cash=round(ending_cash, 2),
            realized_pnl=round(realized_pnl, 2),
            trades=self.trades,
            wins=self.wins,
            losses=self.losses,
            max_drawdown_pct=round(max_dd * 100.0, 2),
            cagr_pct=round(cagr * 100.0, 2),
        )

