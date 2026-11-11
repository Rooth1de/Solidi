import json, urllib.request, time, pandas as pd, sys
def post(body):
    r = urllib.request.Request("https://api.hyperliquid.xyz/info", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    for k in range(4):
        try: return json.load(urllib.request.urlopen(r, timeout=30))
        except Exception: time.sleep(2**k)
    raise RuntimeError(body)
for coin in sys.argv[1:]:
    rows, start = [], 0
    while True:
        b = post({"type": "fundingHistory", "coin": coin, "startTime": start})
        if not b: break
        rows += b; nxt = b[-1]["time"] + 1
        if nxt <= start or len(b) < 500: break
        start = nxt; time.sleep(0.25)
    d = pd.DataFrame(rows).drop_duplicates("time"); d["t"] = pd.to_datetime(d.time, unit="ms", utc=True).dt.floor("h")
    d = d.set_index("t")[["fundingRate", "premium"]].astype(float); d = d[~d.index.duplicated()]
    d.to_csv(f"hl/{coin}.csv"); print(coin, len(d), d.index[0], d.index[-1], "gaps>1h:", (d.index.to_series().diff() > pd.Timedelta("1h")).sum())
