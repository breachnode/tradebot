from typing import Any, Dict, Optional
from .http import HttpClient


class TradierClient:
    def __init__(self, http_client: HttpClient):
        self.http = http_client

    # Accounts / User
    def get_user_profile(self) -> Dict[str, Any]:
        r = self.http.get("user/profile")
        self._raise_for_status(r)
        return r.json()

    def get_accounts(self) -> Dict[str, Any]:
        r = self.http.get("accounts/list")
        self._raise_for_status(r)
        return r.json()

    def get_account_balances(self, account_id: str) -> Dict[str, Any]:
        r = self.http.get(f"accounts/{account_id}/balances")
        self._raise_for_status(r)
        return r.json()

    # Market Data
    def get_quote(self, symbols: str) -> Dict[str, Any]:
        r = self.http.get("markets/quotes", params={"symbols": symbols})
        self._raise_for_status(r)
        return r.json()

    def get_options_chain(self, symbol: str, expiration: str) -> Dict[str, Any]:
        r = self.http.get(
            "markets/options/chains", params={"symbol": symbol, "expiration": expiration}
        )
        self._raise_for_status(r)
        return r.json()

    def get_options_strikes(self, symbol: str, expiration: str) -> Dict[str, Any]:
        r = self.http.get(
            "markets/options/strikes", params={"symbol": symbol, "expiration": expiration}
        )
        self._raise_for_status(r)
        return r.json()

    def get_options_expirations(self, symbol: str, include_all_roots: bool = False) -> Dict[str, Any]:
        r = self.http.get(
            "markets/options/expirations",
            params={"symbol": symbol, "includeAllRoots": str(include_all_roots).lower()},
        )
        self._raise_for_status(r)
        return r.json()

    # Orders
    def preview_option_order(
        self,
        account_id: str,
        option_symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        duration: str = "day",
        order_type: str = "market",
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "class": "option",
            "symbol": option_symbol,
            "side": side,
            "quantity": quantity,
            "type": order_type,
            "duration": duration,
            "preview": "true",
        }
        if price is not None:
            data["price"] = price

        r = self.http.post_form(f"accounts/{account_id}/orders", data=data)
        self._raise_for_status(r)
        return r.json()

    def place_option_order(
        self,
        account_id: str,
        option_symbol: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        duration: str = "day",
        order_type: str = "market",
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "class": "option",
            "symbol": option_symbol,
            "side": side,
            "quantity": quantity,
            "type": order_type,
            "duration": duration,
        }
        if price is not None:
            data["price"] = price

        r = self.http.post_form(f"accounts/{account_id}/orders", data=data)
        self._raise_for_status(r)
        return r.json()

    def cancel_order(self, account_id: str, order_id: str) -> Dict[str, Any]:
        r = self.http.delete(f"accounts/{account_id}/orders/{order_id}")
        self._raise_for_status(r)
        return r.json()

    # Helpers
    @staticmethod
    def _raise_for_status(r):
        if r.status_code == 401:
            auth_header = r.request.headers.get("Authorization", "<missing>")
            raise RuntimeError(
                f"401 Unauthorized from Tradier. Check bearer token formatting and value. Sent header: {auth_header[:25]}..."
            )
        if not (200 <= r.status_code < 300):
            raise RuntimeError(f"HTTP {r.status_code}: {r.text}")

