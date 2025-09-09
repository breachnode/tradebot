import os, json, requests

TOKEN = os.environ.get("TRADIER_TOKEN", "A62MlZvj7Uk08pKrxES3YzgXbp3y")
ACCOUNT = os.environ.get("TRADIER_ACCOUNT", "VA95173921")
BASE = os.environ.get("TRADIER_BASE", "https://sandbox.tradier.com/v1").rstrip("/")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

def get(path, params=None):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=20)
    return r.status_code, r.text

def post(path, data):
    h = dict(HEADERS); h["Content-Type"] = "application/x-www-form-urlencoded"
    r = requests.post(f"{BASE}{path}", headers=h, data=data, timeout=20)
    return r.status_code, r.text

def choose_option(symbol: str):
    # expirations
    sc, body = get("/markets/options/expirations", params={"symbol": symbol, "includeAllRoots": "true"})
    if sc != 200:
        print("EXPIRATIONS_ERR", sc, body)
        return None
    try:
        j = json.loads(body)
        dates = (j.get("expirations") or {}).get("date") or (j.get("expirations") or {}).get("expiration")
        if isinstance(dates, list):
            expiry = dates[0] if dates else None
        elif isinstance(dates, str):
            expiry = dates
        elif isinstance(dates, dict):
            expiry = dates.get("date")
        else:
            expiry = None
    except Exception:
        expiry = None
    if not expiry:
        print("NO_EXPIRY")
        return None

    # chain with greeks
    sc, body = get("/markets/options/chains", params={"symbol": symbol, "expiration": expiry, "greeks": "true"})
    if sc != 200:
        print("CHAINS_ERR", sc, body)
        return None
    try:
        j = json.loads(body)
        opts = (j.get("options") or {}).get("option")
        if not opts:
            return None
        if not isinstance(opts, list):
            opts = [opts]
        # pick ~0.30 absolute delta closest
        best = None
        bestdiff = 1e9
        for o in opts:
            g = o.get("greeks") or {}
            d = g.get("delta")
            if d is None:
                continue
            diff = abs(abs(float(d)) - 0.30)
            if diff < bestdiff:
                bestdiff = diff
                best = o
        if not best:
            return None
        occ = best.get("symbol") or best.get("option_symbol")
        return occ
    except Exception as e:
        print("PARSE_ERR", e)
        return None

def main():
    symbol = os.environ.get("UNDERLYING", "SPY")
    occ = choose_option(symbol)
    print("CHOSEN_OCC", occ)
    if not occ:
        return
    data = {
        "class": "option",
        "symbol": symbol,
        "option_symbol": occ,
        "side": "buy_to_open",
        "quantity": "1",
        "type": "market",
        "duration": "day",
        "tag": "my-bot-test",
    }
    sc, body = post(f"/accounts/{ACCOUNT}/orders", data)
    print("PLACE_OPTION", sc, body)
    order_id = None
    try:
        j = json.loads(body); order_id = (j.get("order") or {}).get("id") or j.get("id")
    except Exception:
        pass
    print("ORDER_ID", order_id)
    if order_id:
        sc, body = get(f"/accounts/{ACCOUNT}/orders/{order_id}")
        print("FETCH_ORDER", sc, body)

if __name__ == "__main__":
    main()

