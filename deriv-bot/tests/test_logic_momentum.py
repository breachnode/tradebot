from deriv_bot.logic.momentum_vwap import MomentumVWAP


def test_entry_on_bias():
    s = MomentumVWAP(0.3, 0.3)
    row = {"close": 10, "vwap": 9, "ema5": 10, "ema20": 9, "volume": 100}
    sig = s.decide_entry(row)
    assert sig and sig["side"] == "long"
