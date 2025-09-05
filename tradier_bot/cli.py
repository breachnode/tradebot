import argparse
import os
import sys
from typing import Optional

from .config import load_config
from .http import HttpClient
from .tradier import TradierClient


def build_client() -> TradierClient:
    cfg = load_config()
    http = HttpClient(base_url=cfg.base_url, bearer_token=cfg.api_token)
    return TradierClient(http)


def cmd_profile(args):
    client = build_client()
    data = client.get_user_profile()
    print(data)


def cmd_accounts(args):
    client = build_client()
    data = client.get_accounts()
    print(data)


def cmd_balances(args):
    client = build_client()
    data = client.get_account_balances(args.account)
    print(data)


def cmd_quote(args):
    client = build_client()
    data = client.get_quote(args.symbols)
    print(data)


def cmd_chain(args):
    client = build_client()
    data = client.get_options_chain(args.symbol, args.expiration)
    print(data)


def cmd_preview(args):
    client = build_client()
    data = client.preview_option_order(
        account_id=args.account,
        option_symbol=args.option_symbol,
        side=args.side,
        quantity=args.quantity,
        price=args.price,
        duration=args.duration,
        order_type=args.type,
    )
    print(data)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Tradier CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("profile", help="Get user profile")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("accounts", help="List accounts")
    p.set_defaults(func=cmd_accounts)

    p = sub.add_parser("balances", help="Get account balances")
    p.add_argument("account", help="Account ID, e.g., VA95173921")
    p.set_defaults(func=cmd_balances)

    p = sub.add_parser("quote", help="Get market quotes")
    p.add_argument("symbols", help="CSV of symbols, e.g., SPY,QQQ")
    p.set_defaults(func=cmd_quote)

    p = sub.add_parser("chain", help="Get options chain for expiry")
    p.add_argument("symbol", help="Underlying symbol, e.g., SPY")
    p.add_argument("expiration", help="YYYY-MM-DD")
    p.set_defaults(func=cmd_chain)

    p = sub.add_parser("preview", help="Preview option order")
    p.add_argument("account", help="Account ID")
    p.add_argument("option_symbol", help="OCC option symbol, e.g., SPY250905C00450000")
    p.add_argument("side", choices=["buy_to_open", "sell_to_close", "sell_to_open", "buy_to_close"], help="Order side")
    p.add_argument("quantity", type=int)
    p.add_argument("--type", default="market", choices=["market", "limit"], help="Order type")
    p.add_argument("--price", type=float, default=None)
    p.add_argument("--duration", default="day", choices=["day", "gtc", "pre", "post"], help="Order duration")
    p.set_defaults(func=cmd_preview)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:  # surface helpful message, keep non-zero exit
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

