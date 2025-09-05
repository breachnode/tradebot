import argparse
import os
import sys
from typing import Optional

from .config import load_config
from .http import HttpClient
from .tradier import TradierClient
from .runner import PaperRunner


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
        underlying_symbol=args.symbol,
        option_symbol=args.option_symbol,
        side=args.side,
        quantity=args.quantity,
        price=args.price,
        duration=args.duration,
        order_type=args.type,
    )
    print(data)


def cmd_test_trade(args):
    client = build_client()
    # 1) Get nearest expiration
    expirations = client.get_options_expirations(args.symbol)
    exp_list = expirations.get("expirations", {}).get("date", [])
    if isinstance(exp_list, str):
        exp_list = [exp_list]
    if not exp_list:
        raise RuntimeError("No expirations returned")
    expiration = exp_list[0]

    # 2) Get chain and pick ATM call or put by midpoint strike
    chain = client.get_options_chain(args.symbol, expiration)
    options = chain.get("options", {}).get("option", [])
    if not options:
        raise RuntimeError("No options returned for chain")
    # Sort by absolute difference between strike and underlying
    # Underlying last from any option quote if available, else midpoint of strikes
    strikes = [o.get("strike") for o in options if o.get("strike") is not None]
    if not strikes:
        raise RuntimeError("No strikes found")
    underlying_guess = sum(strikes) / len(strikes)
    options.sort(key=lambda o: abs((o.get("strike") or underlying_guess) - underlying_guess))
    chosen = options[0]
    occ_symbol = chosen.get("symbol") or chosen.get("option_symbol")
    if not occ_symbol:
        raise RuntimeError("Option symbol missing in chain response")

    # 3) Preview order
    preview = client.preview_option_order(
        account_id=args.account,
        underlying_symbol=args.symbol,
        option_symbol=occ_symbol,
        side=args.side,
        quantity=args.quantity,
        order_type=args.type,
        price=args.price,
        duration=args.duration,
    )
    print({"preview": preview})

    # 4) Place order (non-filling suggested: limit far from market if price provided)
    placed = client.place_option_order(
        account_id=args.account,
        underlying_symbol=args.symbol,
        option_symbol=occ_symbol,
        side=args.side,
        quantity=args.quantity,
        order_type=args.type,
        price=args.price,
        duration=args.duration,
    )
    print({"placed": placed})

    # Extract order id and cancel
    order_id = (
        placed.get("order") and placed["order"].get("id")
    ) or placed.get("id")
    if not order_id:
        raise RuntimeError(f"No order id in response: {placed}")
    # Try a short poll before cancel to let the order register
    try:
        status = client.get_order_status(args.account, str(order_id))
        print({"status": status})
    except Exception as _:
        pass
    try:
        cancelled = client.cancel_order(args.account, str(order_id))
        print({"cancelled": cancelled})
    except Exception as exc:
        print({"cancel_error": str(exc)})


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
    p.add_argument("symbol", help="Underlying symbol, e.g., SPY")
    p.add_argument("option_symbol", help="OCC option symbol, e.g., SPY250905C00450000")
    p.add_argument("side", choices=["buy_to_open", "sell_to_close", "sell_to_open", "buy_to_close"], help="Order side")
    p.add_argument("quantity", type=int)
    p.add_argument("--type", default="market", choices=["market", "limit"], help="Order type")
    p.add_argument("--price", type=float, default=None)
    p.add_argument("--duration", default="day", choices=["day", "gtc", "pre", "post"], help="Order duration")
    p.set_defaults(func=cmd_preview)

    p = sub.add_parser("order-status", help="Get order status")
    p.add_argument("account", help="Account ID")
    p.add_argument("order_id", help="Order ID")
    p.set_defaults(func=lambda a: print(build_client().get_order_status(a.account, a.order_id)))

    p = sub.add_parser("paper-run", help="Run 30m paper test using Yahoo & StockTwits")
    p.add_argument("symbol", help="Underlying symbol, e.g., SPY")
    p.add_argument("--account", default=None, help="Account ID (optional)")
    p.add_argument("--minutes", type=int, default=30, help="Duration minutes")
    p.add_argument("--poll", type=int, default=60, help="Poll seconds")
    p.add_argument("--tp", type=float, default=0.25, help="Take profit percent")
    p.add_argument("--sl", type=float, default=0.20, help="Stop loss percent")
    def _run(a):
        client = build_client()
        PaperRunner(client, a.symbol, a.account, a.minutes, a.poll, a.tp, a.sl).run()
    p.set_defaults(func=_run)

    p = sub.add_parser("test-trade", help="Sandbox test: pick ATM, preview, place, cancel")
    p.add_argument("account", help="Account ID")
    p.add_argument("symbol", help="Underlying symbol, e.g., SPY")
    p.add_argument("side", choices=["buy_to_open", "sell_to_open"], help="Open side for test")
    p.add_argument("quantity", type=int)
    p.add_argument("--type", default="limit", choices=["market", "limit"], help="Order type")
    p.add_argument("--price", type=float, default=0.01, help="Limit price (use non-filling price)")
    p.add_argument("--duration", default="day", choices=["day", "gtc", "pre", "post"], help="Order duration")
    p.set_defaults(func=cmd_test_trade)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:  # surface helpful message, keep non-zero exit
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

