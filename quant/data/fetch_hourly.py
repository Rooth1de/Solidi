"""Yahoo 60m bars (max ~730 days). Timestamps UTC. Equity bars are regular-session only (no prepost)."""
import sys, json, time, urllib.request, pandas as pd
UA = {"User-Agent": "Mozilla/5.0"}
def fetch(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=730d&interval=60m&includePrePost=false"
    j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    d = pd.DataFrame({k: q[k] for k in ("open","high","low","close","volume")}, index=pd.to_datetime(j["timestamp"], unit="s", utc=True))
    return d[~d.index.duplicated()].dropna(subset=["open","high","low","close"])
for s in sys.argv[1:]:
    d = fetch(s); d.to_csv(f"hourly/{s}.csv"); time.sleep(0.5)
    gaps = d.index.to_series().diff().dt.total_seconds().div(3600)
    bad = ((d.high < d[["open","close"]].max(1)) | (d.low > d[["open","close"]].min(1))).sum()
    print(f"{s}: {len(d)} bars {d.index[0]} -> {d.index[-1]} | bars/day {len(d)/d.index.normalize().nunique():.1f} | gaps>1h(non-overnight) {(gaps.between(1.01, 12)).sum()} | zero-range {(d.high==d.low).sum()} | OHLC-inconsistent {bad}")
