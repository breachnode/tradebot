import os, json, time, requests

TOKEN = os.environ.get("TRADIER_TOKEN", "A62MlZvj7Uk08pKrxES3YzgXbp3y")
BASE = os.environ.get("TRADIER_BASE", "https://sandbox.tradier.com/v1").rstrip("/")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

QUERIES = [
    "apple","alphabet","amazon","microsoft","nvidia","meta","tesla","alibaba",
    "semiconductor","chip","ai","software","bank","financial","energy","oil",
    "retail","pharma","biotech","industrial","automotive","cloud","data",
]

def get(path, params=None):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=20)
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None

def is_optionable(symbol: str) -> bool:
    d = get("/markets/options/expirations", params={"symbol": symbol, "includeAllRoots": "true"})
    if not d:
        return False
    exps = (d.get("expirations") or {}).get("date") or (d.get("expirations") or {}).get("expiration")
    return bool(exps)

def main():
    symbols = []
    # seed with common mega caps
    symbols += [
        "SPY","QQQ","AAPL","MSFT","AMZN","NVDA","META","GOOGL","GOOG","TSLA",
        "AMD","NFLX","AVGO","QCOM","CSCO","INTC","AMAT","MU","LRCX","ASML",
        "CRM","ORCL","ADBE","SHOP","PLTR","UBER","COST","DIS","V","MA","JPM","BAC","WMT","NKE","BABA"
    ]
    seen = set(s.upper() for s in symbols)

    for q in QUERIES:
        d = get("/markets/search", params={"q": q, "indexes": "false"})
        if not d:
            continue
        sec = (d.get("securities") or {}).get("security")
        if not sec:
            continue
        if isinstance(sec, dict):
            sec = [sec]
        for s in sec:
            sym = (s.get("symbol") or "").upper()
            typ = (s.get("type") or "").lower()
            if not sym or typ not in ("stock","etf"):
                continue
            if sym not in seen:
                symbols.append(sym)
                seen.add(sym)
        time.sleep(0.1)

    # Filter to optionable and write file
    out = []
    for sym in symbols:
        try:
            if is_optionable(sym):
                out.append(sym)
        except Exception:
            pass
        time.sleep(0.1)

    out = list(dict.fromkeys(out))
    with open("/workspace/curated_symbols.txt", "w") as f:
        f.write("\n".join(out))
    print(f"wrote {len(out)} symbols to /workspace/curated_symbols.txt")

if __name__ == "__main__":
    main()

