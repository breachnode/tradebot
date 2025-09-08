## Tradier Bot: Collector → Analyzer → Simulator → Logic → Bot

U.S.-compliant options trading bot using the Tradier REST API.

### Quick Start

1) Setup
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2) Collector (timesales and OHLC)
```
python collector/stream_timesales.py
python collector/build_ohlc.py
```

3) Backtest
```
python simulator/backtest.py --symbol SPY
```

4) Live bot (tiny size first)
```
python bot/executor.py
```

### Env
See `.env.example` for variables: Tradier token, account id, base URL, symbols, risk.

