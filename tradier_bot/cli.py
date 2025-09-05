import argparse
import os
import sys
from typing import Optional

from .config import load_config
from .http import HttpClient
from .tradier import TradierClient
from .runner import PaperRunner
from .live_runner import LiveRunner
from .symbols_sync import load_symbols_from_file, cross_reference_optionable
from .backtester import Backtester


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
    p.add_argument("--capital", type=float, default=100.0, help="Starting capital ($)")
    def _run(a):
        client = build_client()
        PaperRunner(client, a.symbol, a.account, a.minutes, a.poll, a.tp, a.sl, a.capital).run()
    p.set_defaults(func=_run)

    p = sub.add_parser("live-run", help="Live sandbox runner: momentum+breakout+sentiment with TP/SL and liquidity checks")
    p.add_argument("account", help="Account ID")
    p.add_argument("symbols", nargs="?", default="", help="CSV of underlyings, e.g., SPY,QQQ,AAPL")
    p.add_argument("--symbols-file", default=None, help="Path to newline or comma-separated symbols file")
    p.add_argument("--minutes", type=int, default=30)
    p.add_argument("--poll", type=int, default=30)
    p.add_argument("--tp", type=float, default=0.25)
    p.add_argument("--sl", type=float, default=0.20)
    p.add_argument("--capital", type=float, default=100.0)
    p.add_argument("--maxpos", type=int, default=1)
    p.add_argument("--delta", type=float, default=0.30)
    p.add_argument("--aggr", type=float, default=0.6, help="Aggressiveness 0-1 (higher = more trades)")
    p.add_argument("--min-oi", type=int, default=50, help="Minimum open interest")
    p.add_argument("--max-spread", type=float, default=0.25, help="Max absolute spread ($)")
    p.add_argument("--max-spread-pct", type=float, default=0.35, help="Max spread as % of ask")
    p.add_argument("--min-sent", type=int, default=1, help="Min StockTwits sentiment score magnitude")
    def _live(a):
        client = build_client()
        syms = [s.strip().upper() for s in a.symbols.split(',') if s.strip()]
        if a.symbols_file:
            try:
                with open(a.symbols_file, 'r') as f:
                    content = f.read()
                extra = [s.strip().upper() for s in content.replace('\n', ',').split(',') if s.strip()]
                syms = list(dict.fromkeys(syms + extra))
            except Exception as e:
                print({"warn": f"Failed to read symbols file: {e}"})
        LiveRunner(
            client, a.account, syms, a.capital, a.minutes, a.poll, a.tp, a.sl,
            a.maxpos, a.delta, a.aggr, a.min_oi, a.max_spread, a.max_spread_pct, a.min_sent
        ).run()
    p.set_defaults(func=_live)

    p = sub.add_parser("symbols-sync", help="Cross-reference TradingView list with Tradier optionability")
    p.add_argument("file", help="Path to symbols file (newline or CSV)")
    p.add_argument("--limit", type=int, default=200, help="Max symbols to check")
    p.add_argument("--sleep", type=float, default=0.3, help="Seconds between calls")
    def _sync(a):
        client = build_client()
        syms = load_symbols_from_file(a.file)
        optionable, not_optionable = cross_reference_optionable(client, syms, limit=a.limit, sleep_seconds=a.sleep)
        print({"counts": {"optionable": len(optionable), "not_optionable": len(not_optionable)}})
        print({"optionable": optionable[:50] + (["..."] if len(optionable) > 50 else [])})
        print({"not_optionable": not_optionable[:50] + (["..."] if len(not_optionable) > 50 else [])})
    p.set_defaults(func=_sync)

    p = sub.add_parser("backtest", help="2-year backtest on Yahoo daily bars with $100 start")
    p.add_argument("symbols", nargs="?", default="SPY,QQQ,AAPL,TSLA,NVDA,AMD")
    p.add_argument("--symbols-file", default=None, help="Path to symbols file (newline or CSV)")
    p.add_argument("--years", type=int, default=2)
    p.add_argument("--capital", type=float, default=100.0)
    p.add_argument("--tp", type=float, default=0.25)
    p.add_argument("--sl", type=float, default=0.20)
    p.add_argument("--delta", type=float, default=0.30)
    p.add_argument("--maxpos", type=int, default=1)
    p.add_argument("--hold", type=int, default=10, help="Max hold days")
    p.add_argument("--aggr", type=float, default=0.6)
    p.add_argument("--comm", type=float, default=0.35, help="Commission per contract")
    p.add_argument("--fees", type=float, default=0.00, help="Fees per contract")
    p.add_argument("--entry-slip", type=float, default=0.05, help="Entry slippage fraction")
    p.add_argument("--exit-slip", type=float, default=0.05, help="Exit slippage fraction")
    p.add_argument("--entry-prem", type=float, default=1.00, help="Base entry premium per contract ($)")
    def _bt(a):
        syms = [s.strip().upper() for s in a.symbols.split(',') if s.strip()]
        if a.symbols_file:
            try:
                with open(a.symbols_file, 'r') as f:
                    content = f.read()
                extra = [s.strip().upper() for s in content.replace('\n', ',').split(',') if s.strip()]
                syms = list(dict.fromkeys(syms + extra))
            except Exception as e:
                print({"warn": f"Failed to read symbols file: {e}"})
        bt = Backtester(
            syms, years=a.years, starting_capital=a.capital, tp_pct=a.tp, sl_pct=a.sl,
            target_delta=a.delta, max_positions=a.maxpos, max_hold_days=a.hold, aggressiveness=a.aggr,
            commission_per_contract=a.comm, fees_per_contract=a.fees, entry_slippage_frac=a.entry_slip, exit_slippage_frac=a.exit_slip,
            base_entry_premium=a.entry_prem
        )
        stats = bt.run()
        print({
            "starting_capital": stats.starting_capital,
            "ending_cash": stats.ending_cash,
            "realized_pnl": stats.realized_pnl,
            "trades": stats.trades,
            "wins": stats.wins,
            "losses": stats.losses,
            "max_drawdown_pct": stats.max_drawdown_pct,
            "cagr_pct": stats.cagr_pct,
        })
    p.set_defaults(func=_bt)

    p = sub.add_parser("backtest-sweep", help="Grid search TP/SL/Hold/Delta/Agg/EntryPrem")
    p.add_argument("symbols", nargs="?", default="SPY,QQQ,AAPL,TSLA,NVDA,AMD")
    p.add_argument("--symbols-file", default=None)
    p.add_argument("--years", type=int, default=2)
    p.add_argument("--capital", type=float, default=100.0)
    p.add_argument("--comm", type=float, default=0.35)
    p.add_argument("--fees", type=float, default=0.00)
    p.add_argument("--entry-slip", type=float, default=0.05)
    p.add_argument("--exit-slip", type=float, default=0.05)
    def _sweep(a):
        syms = [s.strip().upper() for s in a.symbols.split(',') if s.strip()]
        if a.symbols_file:
            try:
                with open(a.symbols_file, 'r') as f:
                    content = f.read()
                extra = [s.strip().upper() for s in content.replace('\n', ',').split(',') if s.strip()]
                syms = list(dict.fromkeys(syms + extra))
            except Exception as e:
                print({"warn": f"Failed to read symbols file: {e}"})
        # Preload histories to reuse across runs
        from .backtester import Backtester
        preload = {}
        tmp_bt = Backtester(syms, years=a.years, starting_capital=a.capital)
        for s in syms:
            preload[s] = tmp_bt._fetch_history(s)
        grids = {
            "tp": [0.15, 0.20, 0.25],
            "sl": [0.20, 0.30, 0.35],
            "delta": [0.25, 0.30, 0.35],
            "hold": [5, 10, 15],
            "aggr": [0.6, 0.8, 0.95],
            "entry": [0.60, 0.80, 1.00],
        }
        best = None
        best_stat = -1e9
        results = []
        for tp in grids["tp"]:
            for sl in grids["sl"]:
                for delta in grids["delta"]:
                    for hold in grids["hold"]:
                        for ag in grids["aggr"]:
                            for ent in grids["entry"]:
                                bt = Backtester(
                                    syms, years=a.years, starting_capital=a.capital, tp_pct=tp, sl_pct=sl,
                                    target_delta=delta, max_positions=1, max_hold_days=hold, aggressiveness=ag,
                                    commission_per_contract=a.comm, fees_per_contract=a.fees,
                                    entry_slippage_frac=a.entry_slip, exit_slippage_frac=a.exit_slip,
                                    base_entry_premium=ent, histories_override=preload
                                )
                                st = bt.run()
                                score = st.ending_cash  # simple objective
                                cfg = {"tp": tp, "sl": sl, "delta": delta, "hold": hold, "aggr": ag, "entry": ent}
                                results.append((score, cfg, st))
                                if score > best_stat:
                                    best_stat = score
                                    best = (cfg, st)
        # Print top 5
        results.sort(key=lambda x: x[0], reverse=True)
        top = results[:5]
        print({"best": {"config": top[0][1], "stats": {
            "ending_cash": top[0][2].ending_cash,
            "pnl": top[0][2].realized_pnl,
            "trades": top[0][2].trades,
            "wins": top[0][2].wins,
            "losses": top[0][2].losses,
            "mdd": top[0][2].max_drawdown_pct,
            "cagr": top[0][2].cagr_pct,
        }}})
        for _, cfg, st in top[1:]:
            print({"alt": {"config": cfg, "ending_cash": st.ending_cash, "cagr": st.cagr_pct}})
    p.set_defaults(func=_sweep)

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

