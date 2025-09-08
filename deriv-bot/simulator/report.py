def report(stats: dict) -> str:
    return f"trades={stats.get('trades')} pnl={stats.get('pnl')}"

