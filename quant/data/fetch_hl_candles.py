import json, urllib.request, time, pandas as pd, sys
def post(body):
    r = urllib.request.Request("https://api.hyperliquid.xyz/info", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    for k in range(4):
        try: return json.load(urllib.request.urlopen(r, timeout=30))
        except Exception: time.sleep(2**k)
    raise RuntimeError(body)
now = int(time.time()*1000)
for c in sys.argv[1:]:
    b = post({"type": "candleSnapshot", "req": {"coin": c, "interval": "1d", "startTime": 0, "endTime": now}})
    d = pd.DataFrame(b); d["t"] = pd.to_datetime(d.t, unit="ms", utc=True)
    d = d.set_index("t")[["o","h","l","c","v"]].astype(float); d = d[d.v > 0].iloc[:-1]   # traded days only; drop today
    d.to_csv(f"hl/{c}_1d.csv"); print(c, len(d), d.index[0].date(), d.index[-1].date()); time.sleep(0.3)
