"""Fetch daily adjusted OHLCV from Yahoo v8 chart endpoint -> parquet-free CSV cache.
CAVEAT: universe is *current* liquid names => survivorship bias. ETFs used as primary
universe to limit it; single-stock tests are flagged as contaminated."""
import sys, json, time, urllib.request, pandas as pd
UA = {"User-Agent": "Mozilla/5.0"}
def fetch(sym, start="1993-01-01"):
    p1 = int(pd.Timestamp(start).timestamp()); p2 = int(time.time())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div,splits"
    for k in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30)
            j = json.load(r)["chart"]["result"][0]; break
        except Exception as e:
            time.sleep(2**k); j = None
    if j is None: raise RuntimeError(sym)
    q = j["indicators"]["quote"][0]; adj = j["indicators"]["adjclose"][0]["adjclose"]
    df = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"],
                       "adjclose": adj, "volume": q["volume"]},
                      index=pd.to_datetime(j["timestamp"], unit="s").normalize())
    return df[~df.index.duplicated()].dropna(subset=["close", "adjclose"])
if __name__ == "__main__":
    for s in sys.argv[1:]:
        d = fetch(s); d.to_csv(f"{s}.csv"); print(s, len(d), d.index[0].date(), d.index[-1].date()); time.sleep(0.5)
