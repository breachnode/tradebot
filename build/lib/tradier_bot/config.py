import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv


EnvironmentName = Literal["sandbox", "production"]


@dataclass(frozen=True)
class TradierConfig:
    api_token: str
    environment: EnvironmentName

    @property
    def base_url(self) -> str:
        if self.environment == "sandbox":
            return "https://sandbox.tradier.com/v1"
        return "https://api.tradier.com/v1"


def load_config() -> TradierConfig:
    load_dotenv()
    token = (os.getenv("TRADIER_TOKEN") or "").strip()
    if not token:
        raise RuntimeError(
            "TRADIER_TOKEN is required. Set it in your environment or .env file."
        )

    # Default to sandbox unless explicitly set to production
    env = (os.getenv("TRADIER_ENV") or "sandbox").strip().lower()
    if env not in ("sandbox", "production"):
        raise RuntimeError("TRADIER_ENV must be 'sandbox' or 'production'")

    return TradierConfig(api_token=token, environment=env) 

