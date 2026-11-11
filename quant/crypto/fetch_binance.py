"""Download Binance USD-M perpetual 1m klines + funding history from the public archive
(S3 mirror of data.binance.vision) -> compact .npz per symbol under quant/data/crypto/.
Usage: python fetch_binance.py BTCUSDT ETHUSDT SOLUSDT [--start 2023-01 --end 2026-10]"""
import sys, io, os, zipfile, urllib.request, time, argparse
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/monthly"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "crypto")

def _get(url):
    for k in range(5):
        try:
            return urllib.request.urlopen(url, timeout=120).read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2 ** k)
        except Exception:
            time.sleep(2 ** k)
    raise RuntimeError(url)

def _csv(raw):
    z = zipfile.ZipFile(io.BytesIO(raw)); txt = z.read(z.namelist()[0])
    hdr = 0 if txt[:1].isalpha() else None          # older files have no header row
    return pd.read_csv(io.BytesIO(txt), header=hdr)

def klines(sym, m):
    raw = _get(f"{BASE}/klines/{sym}/1m/{sym}-1m-{m}.zip")
    if raw is None: return None
    d = _csv(raw).iloc[:, [0, 1, 2, 3, 4, 7, 8, 10]]
    d.columns = ["t", "o", "h", "l", "c", "qv", "n", "tbqv"]
    return d

def funding(sym, m):
    raw = _get(f"{BASE}/fundingRate/{sym}/{sym}-fundingRate-{m}.zip")
    if raw is None: return None
    d = _csv(raw).iloc[:, [0, 2]]; d.columns = ["t", "rate"]
    return d

def fetch(sym, months):
    with ThreadPoolExecutor(8) as ex:
        ks = [k for k in ex.map(lambda m: klines(sym, m), months) if k is not None]
        fs = [f for f in ex.map(lambda m: funding(sym, m), months) if f is not None]
    k = pd.concat(ks).drop_duplicates("t").sort_values("t"); f = pd.concat(fs).drop_duplicates("t").sort_values("t")
    t = k.t.values.astype(np.int64)
    if t.max() > 10 ** 14: t //= 1000                # guard against microsecond stamps
    np.savez_compressed(os.path.join(OUT, f"{sym}.npz"), t=t, o=k.o.values, h=k.h.values, l=k.l.values,
                        c=k.c.values, qv=k.qv.values.astype(np.float64), n=k.n.values.astype(np.int32),
                        tbqv=k.tbqv.values.astype(np.float64), ft=f.t.values.astype(np.int64), fr=f.rate.values)
    gaps = int((np.diff(t) != 60000).sum())
    print(sym, len(k), pd.to_datetime(t[0], unit="ms"), pd.to_datetime(t[-1], unit="ms"), "gaps", gaps, "funding", len(f), flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("syms", nargs="+")
    ap.add_argument("--start", default="2023-01"); ap.add_argument("--end", default="2026-10")
    a = ap.parse_args(); os.makedirs(OUT, exist_ok=True)
    months = [str(p) for p in pd.period_range(a.start, a.end, freq="M")]
    for s in a.syms: fetch(s, months)
