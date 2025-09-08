import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
	tradier_token: str = os.getenv("TRADIER_TOKEN", "")
	tradier_account: str = os.getenv("TRADIER_ACCOUNT_ID", "")
	tradier_base: str = os.getenv("TRADIER_BASE", "https://api.tradier.com/v1")
	symbols_csv: str = os.getenv("SYMBOLS", "SPY,QQQ")
	discord_webhook: str = os.getenv("DISCORD_WEBHOOK", "")
	risk_tp_pct: float = float(os.getenv("RISK_TP_PCT", "0.30"))
	risk_sl_pct: float = float(os.getenv("RISK_SL_PCT", "0.30"))
	daily_drawdown: float = float(os.getenv("DAILY_DRAWDOWN", "0.20"))
	max_positions: int = int(os.getenv("MAX_CONCURRENT_POS", "1"))
	position_notional: float = float(os.getenv("POSITION_NOTIONAL", "5"))
	ohlc_interval: str = os.getenv("OHLC_INTERVAL", "1m")
	eod_flat_hhmm: str = os.getenv("EOD_FLAT_HHMM", "1555")

	# Scheduler
	open_hhmm: str = os.getenv("OPEN_HHMM", "0930")
	close_hhmm: str = os.getenv("CLOSE_HHMM", "1600")
	timezone: str = os.getenv("TIMEZONE", "US/Eastern")

	@property
	def symbols(self) -> list[str]:
		return [s.strip().upper() for s in self.symbols_csv.split(",") if s.strip()]


SETTINGS = Settings()