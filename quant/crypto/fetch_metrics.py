"""Download Binance USD-M 5-minute futures metrics (open interest, long/short ratios) -> <SYM>_oi.npz.
Daily archive files; missing days are left as NaN (never forward-filled across a gap > 1 bar here)."""
import sys, io, os, zipfile, urllib.request, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/daily/metrics"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "crypto")

def day(sym, d):
    url = f"{BASE}/{sym}/{sym}-metrics-{d}.zip"
    for k in range(5):
        try:
            raw = urllib.request.urlopen(url, timeout=60).read(); break
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2 ** k)
        except Exception:
            time.sleep(2 ** k)
    else:
        return None
    z = zipfile.ZipFile(io.BytesIO(raw))
    return pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), usecols=[0, 2, 5, 6], header=0,
                       names=["t", "sym", "oi", "oiv", "top_cnt", "top_ls", "ls", "taker_ls"])

def fetch(sym, start="2023-01-01", end="2026-10-31"):
    days = [str(d.date()) for d in pd.date_range(start, end)]
    with ThreadPoolExecutor(24) as ex:
        parts = [p for p in ex.map(lambda d: day(sym, d), days) if p is not None]
    m = pd.concat(parts); m["t"] = pd.to_datetime(m.t).dt.floor("5min")
    m = m.drop_duplicates("t").set_index("t").reindex(pd.date_range(start, pd.Timestamp(end) + pd.Timedelta("23h55min"), freq="5min"))
    np.savez_compressed(os.path.join(OUT, f"{sym}_oi.npz"), t=(m.index.astype("int64") // 10 ** 6).values,
                        oi=m.oi.values.astype(float), top_ls=m.top_ls.values.astype(float), ls=m.ls.values.astype(float))
    print(sym, len(parts), "days of", len(days), "| NaN share", round(float(m.oi.isna().mean()), 4), flush=True)

if __name__ == "__main__":
    for s in sys.argv[1:]: fetch(s)
