from dataclasses import dataclass
from ..common.settings import SETTINGS


@dataclass
class RiskState:
    start_equity: float
    halted: bool = False


def should_halt(equity_now: float, state: RiskState) -> bool:
    dd = (equity_now - state.start_equity) / state.start_equity
    if dd <= -SETTINGS.daily_drawdown:
        state.halted = True
    return state.halted

