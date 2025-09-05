## Tradier Bot (Clean Scaffold)

Requirements: Python 3.10+

### Setup

1. Create and activate a venv
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment
```bash
cp .env.sample .env
edit .env  # set TRADIER_TOKEN and TRADIER_ENV=sandbox or production
```

### CLI Usage

```bash
python -m tradier_bot.cli --help | cat

# Profile
python -m tradier_bot.cli profile

# Accounts and balances
python -m tradier_bot.cli accounts
python -m tradier_bot.cli balances VA95173921

# Quotes and chain
python -m tradier_bot.cli quote SPY,QQQ
python -m tradier_bot.cli chain SPY 2025-09-05

# Preview option order (example OCC symbol only)
python -m tradier_bot.cli preview VA95173921 SPY250905C00450000 buy_to_open 1 --type limit --price 1.23
```

Environment handling automatically sets headers:
- Authorization: Bearer <token>
- Accept: application/json
- Content-Type is added only for POST form requests.

If you see 401, verify your token in `.env`, no hidden characters, and that `TRADIER_ENV` points to the expected environment.

