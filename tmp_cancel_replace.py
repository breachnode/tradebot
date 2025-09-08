import os, json, requests

TOKEN = os.environ.get("TRADIER_TOKEN", "A62MlZvj7Uk08pKrxES3YzgXbp3y")
ACCOUNT = os.environ.get("TRADIER_ACCOUNT", "VA95173921")
BASE = os.environ.get("TRADIER_BASE", "https://sandbox.tradier.com/v1").rstrip("/")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

def get(path, params=None):
    r = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=20)
    return r.status_code, r.text

def delete(path):
    r = requests.delete(f"{BASE}{path}", headers=HEADERS, timeout=20)
    return r.status_code, r.text

def post(path, data):
    h = dict(HEADERS); h["Content-Type"] = "application/x-www-form-urlencoded"
    r = requests.post(f"{BASE}{path}", headers=h, data=data, timeout=20)
    return r.status_code, r.text

def main():
    # 1) Cancel prior pending order if still present
    prior_id = os.environ.get("PRIOR_ORDER_ID", "19362876")
    if prior_id:
        sc, body = get(f"/accounts/{ACCOUNT}/orders/{prior_id}")
        print("STATUS_PRIOR", sc, body[:200])
        if sc == 200 and '"status":"pending"' in body:
            sc, body = delete(f"/accounts/{ACCOUNT}/orders/{prior_id}")
            print("CANCEL_PRIOR", sc, body[:200])

    # 2) Fetch SPY quote ask
    sc, body = get("/markets/quotes", params={"symbols":"SPY"})
    print("QUOTE", sc, body[:240])
    ask = 0.0
    try:
        j = json.loads(body); q = (j.get("quotes") or {}).get("quote")
        if isinstance(q, list): q = q[0]
        ask = float(q.get("ask") or 0)
    except Exception:
        pass
    limit = round(ask + 0.05, 2) if ask else None
    print("ASK", ask, "LIMIT", limit)

    # 3) Place new limit equity buy
    data = {
        "class":"equity","symbol":"SPY","side":"buy","quantity":"1",
        "type":"limit","price": str(limit if limit else "9999"),
        "duration":"day","tag":"fill-now"
    }
    sc, body = post(f"/accounts/{ACCOUNT}/orders", data)
    print("PLACE_LIMIT", sc, body)
    order_id = None
    try:
        j = json.loads(body); order_id = (j.get("order") or {}).get("id") or j.get("id")
    except Exception:
        pass
    print("ORDER_ID", order_id)
    if order_id:
        sc, body = get(f"/accounts/{ACCOUNT}/orders/{order_id}")
        print("FETCH_NEW", sc, body)

    # 4) Positions
    sc, body = get(f"/accounts/{ACCOUNT}/positions")
    print("POSITIONS", sc, body[:240])

if __name__ == "__main__":
    main()

