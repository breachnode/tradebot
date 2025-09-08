import asyncio
from typing import Any, Dict, Optional

from ..common.settings import SETTINGS
from .deriv_ws import DerivWS


class DerivClient:
    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.ws = DerivWS(endpoint)
        self.authorized = False

    async def connect_and_auth(self) -> None:
        await self.ws.connect()
        res = await self.ws.authorize(SETTINGS.deriv_token)
        if "error" in res:
            raise RuntimeError(f"Authorize failed: {res}")
        self.authorized = True

    async def get_balance(self) -> float:
        res = await self.ws.balance()
        bal = (res.get("balance") or {}).get("balance")
        return float(bal) if bal is not None else 0.0

    async def subscribe_ticks(self, symbol: str):
        async for msg in self.ws.subscribe_ticks(symbol):
            yield msg

    async def subscribe_candles(self, symbol: str, granularity: int):
        async for msg in self.ws.subscribe_candles(symbol, granularity):
            yield msg

    async def propose_risefall(self, symbol: str, duration: int = 60, stake: float = 1.0, buy_rise: bool = True) -> Dict[str, Any]:
        # Minimal proposal for rise/fall contract on Deriv
        # See Deriv API docs for full parameters
        params = {
            "proposal": 1,
            "amount": stake,
            "basis": "stake",
            "contract_type": "CALL" if buy_rise else "PUT",
            "currency": "USD",
            "duration": duration,
            "duration_unit": "s",
            "symbol": symbol,
        }
        return await self.ws.propose_contract(**params)

    async def buy(self, proposal_id: str, stake: float) -> Dict[str, Any]:
        return await self.ws.buy(proposal_id, stake)

    async def sell(self, contract_id: str) -> Dict[str, Any]:
        return await self.ws.sell(contract_id)

    async def open_contract_once(self, contract_id: str) -> Dict[str, Any]:
        # One-shot fetch; Deriv supports streaming but for simplicity use one read
        return await self.ws.open_contract(contract_id)

