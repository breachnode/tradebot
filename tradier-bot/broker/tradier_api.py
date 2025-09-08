import requests
from typing import Any, Dict
from ..common.settings import SETTINGS

HEADERS = {
	"Authorization": f"Bearer {SETTINGS.tradier_token}",
	"Accept": "application/json",
}

BASE = SETTINGS.tradier_base.rstrip("/")
ACCOUNT = SETTINGS.tradier_account


def get_balance() -> Dict[str, Any]:
	r = requests.get(f"{BASE}/accounts/{ACCOUNT}/balances", headers=HEADERS, timeout=15)
	r.raise_for_status()
	return r.json()


def get_quote(symbol: str) -> Dict[str, Any]:
	r = requests.get(f"{BASE}/markets/quotes", params={"symbols": symbol}, headers=HEADERS, timeout=15)
	r.raise_for_status()
	q = r.json()["quotes"]["quote"]
	return q if isinstance(q, dict) else q[0]


def get_timesales(symbol: str, interval: str = "1min") -> list[Dict[str, Any]]:
	r = requests.get(f"{BASE}/markets/timesales", params={"symbol": symbol, "interval": interval}, headers=HEADERS, timeout=20)
	r.raise_for_status()
	return (r.json().get("series") or {}).get("data") or []


def get_expirations(symbol: str) -> list[str]:
	r = requests.get(f"{BASE}/markets/options/expirations", params={"symbol": symbol}, headers=HEADERS, timeout=15)
	r.raise_for_status()
	d = r.json()["expirations"]["date"]
	return d if isinstance(d, list) else [d]


def get_chain(symbol: str, expiration: str) -> list[Dict[str, Any]]:
	r = requests.get(f"{BASE}/markets/options/chains", params={"symbol": symbol, "expiration": expiration}, headers=HEADERS, timeout=20)
	r.raise_for_status()
	opts = r.json()["options"]["option"]
	return opts if isinstance(opts, list) else [opts]


def place_option_order(symbol: str, option_symbol: str, side: str, quantity: int = 1, order_type: str = "market") -> Dict[str, Any]:
	data = {
		"class": "option",
		"symbol": symbol,
		"option_symbol": option_symbol,
		"side": side,
		"quantity": str(quantity),
		"type": order_type,
		"duration": "day",
	}
	r = requests.post(
		f"{BASE}/accounts/{ACCOUNT}/orders",
		headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
		data=data,
		timeout=20,
	)
	r.raise_for_status()
	return r.json()