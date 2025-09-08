import asyncio
import json
import websockets
from typing import Any, Dict, Optional, AsyncIterator

from ..common.settings import SETTINGS


class DerivWS:
    def __init__(self, endpoint: Optional[str] = None) -> None:
        self.endpoint = endpoint or SETTINGS.deriv_endpoint
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self) -> None:
        if self.ws and not self.ws.closed:
            return
        self.ws = await websockets.connect(self.endpoint, ping_interval=20, ping_timeout=20)

    async def _send(self, payload: Dict[str, Any]) -> None:
        assert self.ws is not None
        await self.ws.send(json.dumps(payload))

    async def _recv(self) -> Dict[str, Any]:
        assert self.ws is not None
        raw = await self.ws.recv()
        return json.loads(raw)

    async def authorize(self, token: str) -> Dict[str, Any]:
        await self._send({"authorize": token})
        return await self._recv()

    async def balance(self) -> Dict[str, Any]:
        await self._send({"balance": 1})
        return await self._recv()

    async def subscribe_ticks(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        await self._send({"ticks": symbol, "subscribe": 1})
        assert self.ws is not None
        while True:
            msg = await self._recv()
            if "tick" in msg:
                yield msg

    async def subscribe_candles(self, symbol: str, granularity: int) -> AsyncIterator[Dict[str, Any]]:
        await self._send(
            {"ticks_history": symbol, "granularity": granularity, "style": "candles", "subscribe": 1}
        )
        while True:
            msg = await self._recv()
            if "candles" in msg or "ohlc" in msg:
                yield msg

    async def propose_contract(self, **kwargs) -> Dict[str, Any]:
        # Keep generic; caller passes proper fields per Deriv proposal API
        await self._send(kwargs)
        return await self._recv()

    async def buy(self, proposal_id: str, stake: float) -> Dict[str, Any]:
        await self._send({"buy": proposal_id, "price": stake})
        return await self._recv()

    async def sell(self, contract_id: str) -> Dict[str, Any]:
        await self._send({"sell": contract_id})
        return await self._recv()

    async def open_contract(self, contract_id: str) -> Dict[str, Any]:
        await self._send({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1})
        return await self._recv()

