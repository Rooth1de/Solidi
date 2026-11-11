"""Deterministic intraday perp backtest engine (Binance USD-M 1m klines).

Timing contract (no look-ahead):
  * a signal is computed from information <= close of bar t
  * taker entry fills at OPEN of bar t+1, moved against us by `slip`, paying `fee_t`
  * maker entry (optional) rests a limit at close[t] for ONE bar; it fills only if bar t+1 trades
    THROUGH the limit by MAKER_EPS (queue/adverse-selection proxy), paying `fee_m`
  * stop-loss: checked on every bar's high/low, filled at the stop (or the open if gapped) + slip, taker fee
  * take-profit: resting limit, needs price to trade through it, maker fee
  * if stop and target are both inside one bar, the STOP is assumed first (pessimistic)
  * time exit / signal-flip exit: taker at next open
  * funding: charged/credited at the funding timestamp on the position carried into that bar
Returns are per unit of fixed notional, bar by bar (position +1 / -1 / 0), marked to the close.
"""
import os
import numpy as np
from numba import njit

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "crypto")
MAKER_EPS = 0.5e-4          # price must trade 0.5bp through a resting limit to count as filled
YEAR_MIN = 365 * 1440

# ---- cost model: Binance USD-M VIP0 fees; slippage = per-side cost on top of the bar open for
# ---- a ~$50k clip (well under 1% of a typical 1m bar's quote volume on these pairs)
FEE_T, FEE_M = 5.0e-4, 2.0e-4
SLIP = {"BTCUSDT": 1.0e-4, "ETHUSDT": 1.0e-4, "SOLUSDT": 2.0e-4, "XRPUSDT": 2.0e-4,
        "DOGEUSDT": 2.0e-4, "BNBUSDT": 2.0e-4}
CLIP_USD = 50_000.0


def cost(sym, mult=1.0):
    return dict(fee_t=FEE_T * mult, fee_m=FEE_M * mult, slip=SLIP[sym] * mult)


# --------------------------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------------------------
_raw = {}


def _load_raw(sym):
    if sym not in _raw:
        z = np.load(os.path.join(DATA, f"{sym}.npz"))
        _raw[sym] = {k: z[k] for k in z.files}
    return _raw[sym]


def load(sym, tf=5, ref=None, start=None, end=None):
    """Bars at `tf` minutes. Optional `ref` symbol is attached with prefix x_ (same clock)."""
    z = _load_raw(sym)
    n = len(z["t"]) // tf * tf
    D = dict(sym=sym, tf=tf, day=1440 // tf, bpy=YEAR_MIN / tf)
    D["t"] = z["t"][:n:tf].copy()
    _agg(D, z, n, tf, "")
    f = np.zeros(n // tf)
    idx = (np.round(z["ft"] / 60000.0).astype(np.int64) * 60000 - z["t"][0]) // (60000 * tf)
    ok = (idx >= 0) & (idx < len(f))
    np.add.at(f, idx[ok], z["fr"][ok])
    D["fund"] = f
    oip = os.path.join(DATA, f"{sym}_oi.npz")
    if tf % 5 == 0 and os.path.exists(oip):
        # doi[i] = log change of open interest DURING bar i (snapshot at bar close vs bar open).
        # It travels with its bar under permutation. Strategies must lag it one bar (publication delay).
        m = np.load(oip); assert m["t"][0] * (1000 if m["t"][0] < 10 ** 11 else 1) == z["t"][0]
        oi = m["oi"][::tf // 5][:n // tf + 1]
        oi = np.concatenate((oi, np.full(n // tf + 1 - len(oi), np.nan)))
        with np.errstate(all="ignore"):
            d = np.diff(np.log(oi))
        D["doi"] = np.where(np.isfinite(d), d, 0.0)
    if ref:
        zr = _load_raw(ref)
        assert zr["t"][0] == z["t"][0] and len(zr["t"]) == len(z["t"])
        _agg(D, zr, n, tf, "x_")
    if start or end:
        lo = 0 if start is None else int(np.searchsorted(D["t"], _ms(start)))
        hi = len(D["t"]) if end is None else int(np.searchsorted(D["t"], _ms(end)))
        D = cut(D, lo, hi)
    return D


def _agg(D, z, n, tf, pre):
    r = lambda a: a[:n].reshape(-1, tf)
    D[pre + "o"] = r(z["o"])[:, 0].copy()
    D[pre + "h"] = r(z["h"]).max(1)
    D[pre + "l"] = r(z["l"]).min(1)
    D[pre + "c"] = r(z["c"])[:, -1].copy()
    D[pre + "qv"] = r(z["qv"]).sum(1)
    D[pre + "tb"] = r(z["tbqv"]).sum(1)


def _ms(s):
    return int(np.datetime64(s, "ms").astype(np.int64))


ARR = ("o", "h", "l", "c", "qv", "tb")


def cut(D, lo, hi):
    out = {k: (v[lo:hi] if isinstance(v, np.ndarray) else v) for k, v in D.items() if k != "_m"}
    return out


# --------------------------------------------------------------------------------------------
# rolling helpers (causal: value at i uses bars i-w+1 .. i)
# --------------------------------------------------------------------------------------------
def rsum(x, w):
    cs = np.cumsum(np.nan_to_num(x))
    out = np.full(len(x), np.nan)
    out[w - 1:] = cs[w - 1:] - np.concatenate(([0.0], cs[:-w]))
    return out


def rmean(x, w):
    return rsum(x, w) / w


def rstd(x, w):
    m = rmean(x, w)
    v = rmean(x * x, w) - m * m
    return np.sqrt(np.maximum(v, 0.0))


def lagdiff(x, n):
    out = np.full(len(x), np.nan)
    out[n:] = x[n:] - x[:-n]
    return out


# --------------------------------------------------------------------------------------------
# simulator
# --------------------------------------------------------------------------------------------
@njit(cache=True)
def sim(o, h, l, c, fund, sig, sl, tp, max_hold, fee_t, fee_m, slip, maker_entry, flip_exit, eps):
    n = len(c)
    ret = np.zeros(n)
    cap = n + 2
    t_in = np.empty(cap, np.int64); t_out = np.empty(cap, np.int64)
    t_pnl = np.empty(cap); t_dir = np.empty(cap, np.int8)
    nt = 0
    pos = 0; held = 0; ei = 0
    stop = 0.0; take = 0.0; tr = 0.0
    for i in range(1, n):
        r = 0.0; x = 0.0; px = 0.0
        ref = c[i - 1]
        if pos != 0:
            if fund[i] != 0.0:
                r -= pos * fund[i]; tr -= pos * fund[i]
            if held >= max_hold or (flip_exit and sig[i - 1] == -pos):
                px = o[i] * (1.0 - pos * slip)
                x = pos * (px / ref - 1.0) - fee_t
                r += x; tr += x
                t_in[nt] = ei; t_out[nt] = i; t_pnl[nt] = tr; t_dir[nt] = pos; nt += 1
                pos = 0
        new = False
        if pos == 0 and sig[i - 1] != 0:
            d = sig[i - 1]
            if maker_entry:
                lim = c[i - 1]
                if (d > 0 and l[i] < lim * (1.0 - eps)) or (d < 0 and h[i] > lim * (1.0 + eps)):
                    pos = d; ref = lim; r -= fee_m; tr = -fee_m; new = True
            else:
                pos = d; ref = o[i] * (1.0 + d * slip); r -= fee_t; tr = -fee_t; new = True
            if new:
                held = 0; ei = i
                stop = ref * (1.0 - pos * sl[i - 1]) if sl[i - 1] > 0.0 else 0.0
                take = ref * (1.0 + pos * tp[i - 1]) if tp[i - 1] > 0.0 else 0.0
        if pos != 0:
            done = False
            if stop > 0.0:
                if pos > 0 and l[i] <= stop:
                    px = min(stop, o[i]) * (1.0 - slip); done = True
                elif pos < 0 and h[i] >= stop:
                    px = max(stop, o[i]) * (1.0 + slip); done = True
                if done:
                    x = pos * (px / ref - 1.0) - fee_t
            if (not done) and take > 0.0 and not (new and maker_entry):
                if pos > 0 and h[i] > take:
                    px = max(take, o[i]); done = True
                elif pos < 0 and l[i] < take:
                    px = min(take, o[i]); done = True
                if done:
                    x = pos * (px / ref - 1.0) - fee_m
            if done:
                r += x; tr += x
                t_in[nt] = ei; t_out[nt] = i; t_pnl[nt] = tr; t_dir[nt] = pos; nt += 1
                pos = 0
            else:
                x = pos * (c[i] / ref - 1.0)
                r += x; tr += x; held += 1
        ret[i] = r
    return ret, t_in[:nt], t_out[:nt], t_pnl[:nt], t_dir[:nt]


def run(D, spec, cst):
    """spec = dict(sig, sl, tp, max_hold, maker_entry=False, flip_exit=False)"""
    n = len(D["c"])
    z = np.zeros(n)
    sig = np.nan_to_num(spec["sig"]).astype(np.int8)
    sl = np.nan_to_num(spec.get("sl", z)) if spec.get("sl") is not None else z
    tp = np.nan_to_num(spec.get("tp", z)) if spec.get("tp") is not None else z
    return sim(D["o"], D["h"], D["l"], D["c"], D["fund"], sig, sl, tp, int(spec["max_hold"]),
               cst["fee_t"], cst["fee_m"], cst["slip"], bool(spec.get("maker_entry", False)),
               bool(spec.get("flip_exit", False)), MAKER_EPS)


# --------------------------------------------------------------------------------------------
# metrics (all computed by the engine; the researcher only reads them)
# --------------------------------------------------------------------------------------------
def sharpe(r, bpy):
    s = r.std()
    return float(r.mean() / s * np.sqrt(bpy)) if s > 0 else 0.0


def bar_metrics(r, bpy):
    eq = np.cumsum(r)
    dd = float((eq - np.maximum.accumulate(eq)).min()) if len(r) else 0.0
    g, b = r[r > 0].sum(), -r[r < 0].sum()
    yrs = len(r) / bpy
    return dict(net=round(float(r.sum()), 4), ann_ret=round(float(r.sum() / yrs), 4) if yrs else 0,
                sharpe=round(sharpe(r, bpy), 2), pf_bar=round(float(g / b), 3) if b > 0 else None,
                maxdd=round(dd, 4), exposure=round(float((r != 0).mean()), 4))


def trade_metrics(t_in, t_out, pnl, d, tf, yrs):
    n = len(pnl)
    if n == 0:
        return dict(trades=0)
    w = pnl > 0
    gl = pnl[~w].sum()
    return dict(trades=int(n), trades_per_day=round(n / (yrs * 365), 2), win=round(float(w.mean()), 3),
                avg_bps=round(float(pnl.mean() * 1e4), 2), med_bps=round(float(np.median(pnl) * 1e4), 2),
                avg_win_bps=round(float(pnl[w].mean() * 1e4), 1) if w.any() else None,
                avg_loss_bps=round(float(pnl[~w].mean() * 1e4), 1) if (~w).any() else None,
                pf_trade=round(float(pnl[w].sum() / -gl), 3) if gl < 0 else None,
                t_stat=round(float(pnl.mean() / pnl.std() * np.sqrt(n)), 2) if n > 2 and pnl.std() > 0 else 0.0,
                avg_hold_min=round(float((t_out - t_in).mean() * tf), 1),
                long_share=round(float((d > 0).mean()), 3),
                long_avg_bps=round(float(pnl[d > 0].mean() * 1e4), 2) if (d > 0).any() else None,
                short_avg_bps=round(float(pnl[d < 0].mean() * 1e4), 2) if (d < 0).any() else None,
                worst_bps=round(float(pnl.min() * 1e4), 1))


def participation(D, t_in):
    """Clip size as a share of the entry bar's quote volume (liquidity sanity check)."""
    if len(t_in) == 0:
        return None
    p = CLIP_USD / np.maximum(D["qv"][t_in], 1.0)
    return dict(median=round(float(np.median(p)), 5), p99=round(float(np.quantile(p, 0.99)), 5))


# --------------------------------------------------------------------------------------------
# bar permutation (Masters): shuffles intrabar shapes and inter-bar gaps independently, so every
# permuted series has exactly the same bars / same total drift / same return distribution, but no
# temporal structure. Volume and taker-flow travel with their bar. With a `ref` symbol the SAME
# permutation is applied, so contemporaneous cross-asset correlation survives and lead-lag dies.
# Bars [0..start] are left untouched (used by the walk-forward permutation test).
# --------------------------------------------------------------------------------------------
@njit(cache=True)
def _perm_px(o, h, l, c, i1, i2, start):
    n = len(c)
    no = o.copy(); nh = h.copy(); nl = l.copy(); nc = c.copy()
    for i in range(start + 1, n):
        j = i1[i - start - 1]; k = i2[i - start - 1]
        no[i] = nc[i - 1] * (o[k] / c[k - 1])
        nh[i] = no[i] * (h[j] / o[j])
        nl[i] = no[i] * (l[j] / o[j])
        nc[i] = no[i] * (c[j] / o[j])
    return no, nh, nl, nc


def permute(D, seed, start=0):
    n = len(D["c"])
    rng = np.random.default_rng(seed)
    base = np.arange(start + 1, n)
    i1 = rng.permutation(base); i2 = rng.permutation(base)
    P = {k: v for k, v in D.items() if k != "_m"}       # never share the feature cache
    for pre in ("", "x_"):
        if pre + "c" not in D:
            continue
        P[pre + "o"], P[pre + "h"], P[pre + "l"], P[pre + "c"] = _perm_px(
            D[pre + "o"], D[pre + "h"], D[pre + "l"], D[pre + "c"], i1, i2, start)
        for k in ("qv", "tb", "doi"):
            if pre + k not in D:
                continue
            a = D[pre + k].copy(); a[start + 1:] = D[pre + k][i1]; P[pre + k] = a
    return P
