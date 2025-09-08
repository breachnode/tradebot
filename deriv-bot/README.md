## Deriv Options Bot: Collector → Analyzer → Simulator → Logic → Bot

Production-ready modular trading system for Deriv WebSocket API.

### Quick Start

1) Setup
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2) Run collector (ticks and OHLC)
```
python collector/stream_ticks.py
python collector/build_ohlc.py
```

3) Backtest
```
python simulator/backtest.py --symbol R_100
```

4) Live bot (small stake first)
```
python bot/executor.py
```

### Env
See `.env.example` for required variables: Deriv app id, token, symbols, risk.

### Tooling
- Python 3.11, asyncio, websockets
- SQLite storage, CSV exports
- Docker + docker-compose
- ruff + pytest

