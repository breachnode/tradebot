from deriv_bot.bot.risk import RiskState, should_halt


def test_daily_dd_halt():
    st = RiskState(start_equity=100)
    assert not should_halt(90, st)
    assert should_halt(79, st)
