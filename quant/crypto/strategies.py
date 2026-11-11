"""Hypothesis-driven intraday strategies. Each returns a spec for engine.run().
Every feature at bar i uses only bars <= i. GRID lists are the exact parameter ranges tested."""
import itertools
import numpy as np
from engine import rsum, rmean, rstd, lagdiff


def _grid(**kw):
    keys = list(kw)
    return [dict(zip(keys, v)) for v in itertools.product(*kw.values())]


def _r1(D, pre=""):
    lc = np.log(D[pre + "c"])
    return lc, np.concatenate(([0.0], np.diff(lc)))


def _memo(D, key, f):
    """Per-dataset feature cache (features depend on few parameters; the grid re-uses them)."""
    m = D.setdefault("_m", {})
    if key not in m:
        m[key] = f()
    return m[key]


def _volratio(D, N, W):
    return _memo(D, ("vr", N, W), lambda: rsum(D["qv"], N) / (rmean(D["qv"], W) * N))


def _zmove(D, N):
    """N-bar log return and its z-score against trailing 1-day bar volatility."""
    def f():
        lc, r1 = _r1(D)
        rN = lagdiff(lc, N)
        return rN, rN / (rstd(r1, D["day"]) * np.sqrt(N))
    return _memo(D, ("zm", N), f)


def _doiN(D, N):
    # lag: bar i sees open interest only up to bar i-1's close (publication delay)
    return _memo(D, ("doi", N), lambda: rsum(np.concatenate(([0.0], D["doi"][:-1])), N))


# ---- H1: taker-flow imbalance (order-flow proxy). dr=+1 follow the aggressor, -1 fade it. ----
def flow(D, p):
    N, z, hold, dr = p["N"], p["z"], p["hold"], p["dr"]
    W = 3 * D["day"]
    imb = rsum(2.0 * D["tb"] - D["qv"], N) / rsum(D["qv"], N)
    zs = (imb - rmean(imb, W)) / rstd(imb, W)
    vr = _volratio(D, N, W)
    _, r1 = _r1(D)
    sg = rstd(r1, D["day"])
    sig = dr * (((zs > z) & (vr > 1.0)).astype(np.int8) - ((zs < -z) & (vr > 1.0)).astype(np.int8))
    return dict(sig=sig, sl=3.0 * sg * np.sqrt(hold), max_hold=hold)


flow.GRID = _grid(N=[3, 6, 12], z=[1.5, 2.5, 3.5], hold=[3, 6, 12], dr=[1, -1])


# ---- H2: volatility/volume shock (liquidation-cascade proxy). dr=-1 fade exhaustion, +1 ride. ----
def shock(D, p):
    N, z, v, hold, dr = p["N"], p["z"], p["v"], p["hold"], p["dr"]
    rN, zz = _zmove(D, N)
    vr = _volratio(D, N, D["day"])
    sig = dr * (((zz > z) & (vr > v)).astype(np.int8) - ((zz < -z) & (vr > v)).astype(np.int8))
    return dict(sig=sig, sl=np.abs(rN), max_hold=hold)      # stop: move extends by its own size again


shock.GRID = _grid(N=[3, 6, 12], z=[3.0, 4.0, 5.0], v=[1.5, 3.0], hold=[3, 6, 12, 24], dr=[-1, 1])


# ---- H3: funding-extreme fade into settlement (crowded side pays; lean against it, collect). ----
def funding(D, p):
    thr, lead, after = p["thr"], p["lead"], p["after"]
    f = D["fund"]
    idx = np.where(f != 0, np.arange(len(f)), 0)
    last = f[np.maximum.accumulate(idx)]                     # last settled rate known at bar i
    dev = last - 1.0e-4                                      # 1bp/8h is the neutral baseline
    per = 480 // D["tf"]
    tod = ((D["t"] // 60000 // D["tf"]) + 1) % per           # entry bar's offset inside the 8h cycle
    at = tod == (per - lead) % per
    sig = np.where(at & (dev > thr), -1, np.where(at & (dev < -thr), 1, 0)).astype(np.int8)
    return dict(sig=sig, sl=None, max_hold=lead + after)


funding.GRID = _grid(thr=[1.0e-4, 2.0e-4, 4.0e-4], lead=[2, 4, 8, 16], after=[0, 4, 16])


# ---- H4: session / time-of-day drift. One trade per day in a fixed UTC window. ----
def session(D, p):
    h0, w, dr = p["h0"], p["w"], p["dr"]
    per = D["day"]
    nxt = ((D["t"] // 60000 // D["tf"]) + 1) % per
    sig = np.where(nxt == h0 * (60 // D["tf"]), dr, 0).astype(np.int8)
    return dict(sig=sig, sl=None, max_hold=w * (60 // D["tf"]))


session.GRID = _grid(h0=list(range(24)), w=[1, 2, 4], dr=[1, -1])


# ---- H5: BTC -> alt lead-lag. BTC shocks; trade the alt that has not caught up yet. ----
def leadlag(D, p):
    N, z, g, hold = p["N"], p["z"], p["g"], p["hold"]
    lb, rb1 = _r1(D, "x_")
    la, _ = _r1(D)
    rb = lagdiff(lb, N); ra = lagdiff(la, N)
    zb = rb / (rstd(rb1, D["day"]) * np.sqrt(N))
    up = (zb > z) & (ra < g * rb)
    dn = (zb < -z) & (ra > g * rb)
    sig = up.astype(np.int8) - dn.astype(np.int8)
    return dict(sig=sig, sl=np.abs(rb), max_hold=hold)


leadlag.GRID = _grid(N=[1, 3], z=[3.0, 5.0, 7.0], g=[0.5, 1.0], hold=[2, 5, 10])



# ---- H6: liquidation flush. A sharp move while open interest COLLAPSES = forced closing, not new
# ---- information -> fade it once the forced flow is done. OI is used with a one-bar lag. ----
def oiflush(D, p):
    N, z, q, hold = p["N"], p["z"], p["q"], p["hold"]
    rN, zz = _zmove(D, N)
    dN = _doiN(D, N)
    sig = ((zz < -z) & (dN < -q)).astype(np.int8) - ((zz > z) & (dN < -q)).astype(np.int8)
    return dict(sig=sig, sl=np.abs(rN), max_hold=hold)


oiflush.GRID = _grid(N=[6, 12, 24], z=[2.0, 3.0, 4.0], q=[0.005, 0.01, 0.02], hold=[6, 12, 24])


# ---- H7: positioning build-up. A sharp move while open interest EXPANDS = fresh leveraged entries
# ---- chasing -> dr=+1 ride it (new money), dr=-1 fade it (late crowd gets trapped). ----
def oibuild(D, p):
    N, z, q, hold, dr = p["N"], p["z"], p["q"], p["hold"], p["dr"]
    rN, zz = _zmove(D, N)
    dN = _doiN(D, N)
    sig = dr * (((zz > z) & (dN > q)).astype(np.int8) - ((zz < -z) & (dN > q)).astype(np.int8))
    return dict(sig=sig, sl=np.abs(rN), max_hold=hold)


oibuild.GRID = _grid(N=[6, 12, 24], z=[2.0, 3.0], q=[0.005, 0.01, 0.02], hold=[6, 12, 24], dr=[1, -1])



# ---- H6b: long-only liquidation flush (gen 4). Motivation from H6's failure: the short side lost in
# ---- sample (short squeezes keep running), and an 81-set grid made walk-forward selection unstable.
def oiflush_long(D, p):
    N, z, q, hold = p["N"], p["z"], p["q"], p["hold"]
    rN, zz = _zmove(D, N)
    sig = ((zz < -z) & (_doiN(D, N) < -q)).astype(np.int8)
    return dict(sig=sig, sl=np.abs(rN), max_hold=hold)


oiflush_long.GRID = _grid(N=[12, 24], z=[3.0, 4.0], q=[0.01, 0.02], hold=[6, 12])

REG = dict(oiflush_long=oiflush_long, oiflush=oiflush, oibuild=oibuild, flow=flow, shock=shock, funding=funding, session=session, leadlag=leadlag)
