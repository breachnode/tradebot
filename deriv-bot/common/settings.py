import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    deriv_app_id: str = os.getenv("DERIV_APP_ID", "")
    deriv_token: str = os.getenv("DERIV_API_TOKEN", "")
    deriv_endpoint: str = os.getenv("DERIV_ENDPOINT", "")
    symbols: list[str] = tuple(os.getenv("SYMBOLS", "R_100").split(";"))
    discord_webhook: str = os.getenv("DISCORD_WEBHOOK", "")

    risk_tp_pct: float = float(os.getenv("RISK_TP_PCT", "0.30"))
    risk_sl_pct: float = float(os.getenv("RISK_SL_PCT", "0.30"))
    daily_drawdown: float = float(os.getenv("DAILY_DRAWDOWN", "0.20"))
    max_positions: int = int(os.getenv("MAX_CONCURRENT_POS", "1"))
    position_notional: float = float(os.getenv("POSITION_NOTIONAL", "10"))
    ohlc_interval: str = os.getenv("OHLC_INTERVAL", "1m")
    eod_flat_hhmm: str = os.getenv("EOD_FLAT_HHMM", "2355")


SETTINGS = Settings()

