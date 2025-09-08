import pandas as pd
from deriv_bot.analyzer.indicators import ema, rsi


def test_ema_simple():
    s = pd.Series([1, 2, 3, 4, 5])
    e = ema(s, 3)
    assert len(e) == 5


def test_rsi_bounds():
    s = pd.Series([1, 2, 3, 2, 1, 2, 3])
    r = rsi(s, 3)
    assert r.min() >= 0 and r.max() <= 100
