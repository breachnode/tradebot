from .base import Strategy


class MomentumVWAP(Strategy):
    def __init__(self, tp_pct: float, sl_pct: float, min_volume: float = 1.0, cooldown_bars: int = 0):
        self.tp = tp_pct
        self.sl = sl_pct
        self.min_volume = min_volume
        self.cooldown = cooldown_bars
        self.cool = 0

    def decide_entry(self, row) -> dict | None:
        if self.cool > 0:
            self.cool -= 1
            return None
        if row["volume"] < self.min_volume:
            return None
        long_bias = row["close"] > row["vwap"] and row["ema5"] > row["ema20"]
        if long_bias:
            self.cool = self.cooldown
            return {"side": "long", "tp_pct": self.tp, "sl_pct": self.sl}
        return None

    def decide_exit(self, position, row) -> dict | None:
        # exits handled by risk module; can add pattern exits here if needed
        return None

