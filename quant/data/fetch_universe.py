import pandas as pd, time, os, sys, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
D = os.path.dirname(os.path.abspath(__file__)); out = os.path.join(D, "stocks"); os.makedirs(out, exist_ok=True)
h = pd.read_csv(os.path.join(D, "ext/sp500_hist.csv"), parse_dates=["date"])
h = h[h.date >= "2003-01-01"]; tick = sorted({t for s in h.tickers for t in s.split(",")})
UA = {"User-Agent": "Mozilla/5.0"}; p1 = int(pd.Timestamp("2002-01-01").timestamp()); p2 = int(time.time())
def get(t):
    p = os.path.join(out, f"{t}.csv")
    if os.path.exists(p): return t, "ok"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t.replace('.','-')}?period1={p1}&period2={p2}&interval=1d&events=div,splits"
    for k in range(2):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))["chart"]["result"][0]
            q = j["indicators"]["quote"][0]; adj = j["indicators"]["adjclose"][0]["adjclose"]
            df = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"], "adjclose": adj, "volume": q["volume"]},
                              index=pd.to_datetime(j["timestamp"], unit="s").normalize())
            df[~df.index.duplicated()].dropna(subset=["close","adjclose"]).to_csv(p); return t, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404: return t, "missing"
            time.sleep(3)
        except Exception: time.sleep(2)
    return t, "missing"
with ThreadPoolExecutor(8) as ex: res = list(ex.map(get, tick))
miss = [t for t, s in res if s != "ok"]; open(os.path.join(out, "_missing.txt"), "w").write("\n".join(miss))
print("tickers", len(tick), "ok", len(tick)-len(miss), "missing", len(miss))
