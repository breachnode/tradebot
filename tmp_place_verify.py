import os, sys, time, json, requests

TOKEN = os.environ.get("TRADIER_TOKEN", "A62MlZvj7Uk08pKrxES3YzgXbp3y")
ACCOUNT = os.environ.get("TRADIER_ACCOUNT", "VA95173921")
BASE = os.environ.get("TRADIER_BASE", "https://sandbox.tradier.com/v1").rstrip("/")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
}

def get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    return r.status_code, r.text

def post(url, data):
    h = dict(HEADERS)
    h["Content-Type"] = "application/x-www-form-urlencoded"
    r = requests.post(url, headers=h, data=data, timeout=20)
    return r.status_code, r.text

def main():
    # Profile sanity
    sc, body = get(f"{BASE}/user/profile")
    print("PROFILE", sc, body[:200])

    # Place 1-share SPY market buy
    data = {
        "class": "equity",
        "symbol": "SPY",
        "side": "buy",
        "quantity": "1",
        "type": "market",
        "duration": "day",
        "tag": "my-bot-test",
    }
    sc, body = post(f"{BASE}/accounts/{ACCOUNT}/orders", data)
    print("PLACE_EQUITY", sc, body)

    order_id = None
    try:
        j = json.loads(body)
        order_id = (j.get("order") or {}).get("id") or j.get("id")
    except Exception:
        pass
    print("ORDER_ID", order_id)

    if order_id:
        sc, body = get(f"{BASE}/accounts/{ACCOUNT}/orders/{order_id}")
        print("FETCH_ORDER", sc, body)

    sc, body = get(f"{BASE}/accounts/{ACCOUNT}/positions")
    print("POSITIONS", sc, body)

if __name__ == "__main__":
    main()

