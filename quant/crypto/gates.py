"""4-gate validation runner. Thresholds below are fixed BEFORE looking at any result.

  Gate 1  in-sample (2023-01..2024-12): optimise the grid, require a real-looking, plateau-shaped edge
  Gate 2  in-sample permutation test: re-optimise the whole grid on N bar-permuted series
  Gate 3  walk-forward over 2023-01..2026-10: train 180d -> trade next 30d, roll
  Gate 4  walk-forward permutation: permute only the bars after the first training window, redo Gate 3

Usage: python gates.py <strategy> <SYMBOL[,SYMBOL...]> [--tf 5] [--ref BTCUSDT] [--perms 500] [--all] [--maker]
"""
import sys, os, json, time, argparse
import multiprocessing as mp
import numpy as np
import engine as E
from strategies import REG

IS_START, IS_END = "2023-01-01", "2025-01-01"
TRAIN_BLOCKS, BLOCK_DAYS = 6, 30
MIN_TR_IS, MIN_TR_TRAIN = 100, 20
G1 = dict(sharpe=1.0, trades=200, pf_trade=1.10, maxdd=-0.25, neigh_med_sharpe=0.0)
G2_P, G3_SHARPE, G4_P = 0.05, 1.0, 0.01
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "crypto_experiments.jsonl")


def eval_grid(Ds, fn, grid, csts, extra=None):
    """One result per parameter set. With several symbols the SAME parameters are traded on each and the
    book is the equal-weight average (1/k notional per symbol); trades are pooled."""
    out = []
    for p in grid:
        parts = []
        for D, c in zip(Ds, csts):
            spec = fn(D, p)
            if extra: spec.update(extra)
            parts.append(E.run(D, spec, c))
        if len(parts) == 1:
            out.append(parts[0]); continue
        k = len(parts)
        out.append((sum(x[0] for x in parts) / k, np.concatenate([x[1] for x in parts]),
                    np.concatenate([x[2] for x in parts]), np.concatenate([x[3] for x in parts]),
                    np.concatenate([x[4] for x in parts])))
    return out


def objective(r, ntr, bpy, mintr):
    return E.sharpe(r, bpy) if ntr >= mintr else 0.0


def best_of_grid(D, fn, grid, cst, extra):
    res = eval_grid(D, fn, grid, cst, extra)
    obj = np.array([objective(x[0], len(x[1]), D[0]["bpy"], MIN_TR_IS) for x in res])
    return obj, res


def neighbours(grid, i):
    keys = list(grid[0]); axes = {k: sorted({g[k] for g in grid}) for k in keys}
    out = []
    for j, g in enumerate(grid):
        diff = [k for k in keys if g[k] != grid[i][k]]
        if len(diff) == 1 and abs(axes[diff[0]].index(g[diff[0]]) - axes[diff[0]].index(grid[i][diff[0]])) == 1 \
                and not (diff[0] == "dr"):
            out.append(j)
    return out


def walk_forward(D, fn, grid, cst, extra):
    """Returns OOS bar returns, chosen param index per fold, and the OOS trades."""
    B = BLOCK_DAYS * D[0]["day"]; nb = len(D[0]["c"]) // B
    res = eval_grid(D, fn, grid, cst, extra)
    S = np.array([x[0][:nb * B].reshape(nb, B).sum(1) for x in res])
    Q = np.array([(x[0][:nb * B] ** 2).reshape(nb, B).sum(1) for x in res])
    N = np.array([np.bincount(np.minimum(x[1] // B, nb - 1), minlength=nb)[:nb] for x in res])
    oos = np.zeros(nb * B); picks = []; tr = [[], [], [], []]
    for k in range(TRAIN_BLOCKS, nb):
        sl = slice(k - TRAIN_BLOCKS, k); m = TRAIN_BLOCKS * B
        mu = S[:, sl].sum(1) / m; var = Q[:, sl].sum(1) / m - mu ** 2
        sh = np.where(var > 0, mu / np.sqrt(np.maximum(var, 1e-300)) * np.sqrt(D[0]["bpy"]), 0.0)
        sh[N[:, sl].sum(1) < MIN_TR_TRAIN] = 0.0
        j = int(sh.argmax())
        if sh[j] <= 0:                      # nothing made money in training -> stay flat
            picks.append(-1); continue
        picks.append(j)
        r, ti, to, pn, d = res[j]
        oos[k * B:(k + 1) * B] = r[k * B:(k + 1) * B]
        w = (ti >= k * B) & (ti < (k + 1) * B)
        for a, b in zip(tr, (ti[w], to[w], pn[w], d[w])): a.append(b)
    tr = [np.concatenate(a) if a else np.array([]) for a in tr]
    return oos[TRAIN_BLOCKS * B:], picks, tr, TRAIN_BLOCKS * B


# ---- permutation workers (fork: data shared copy-on-write, fully deterministic via seeds) ----
_G = {}


def _w2(seed):
    P = [E.permute(D, seed) for D in _G["D"]]          # same seed -> same shuffle on every symbol
    return float(best_of_grid(P, _G["fn"], _G["grid"], _G["cst"], _G["extra"])[0].max())


def _w4(seed):
    P = [E.permute(D, seed, start=_G["start"]) for D in _G["D"]]
    oos = walk_forward(P, _G["fn"], _G["grid"], _G["cst"], _G["extra"])[0]
    return E.sharpe(oos, _G["D"][0]["bpy"])


def _pool(fn, D, strat, grid, cst, extra, n, start=0, seed0=0):
    _G.update(D=D, fn=strat, grid=grid, cst=cst, extra=extra, start=start)
    with mp.get_context("fork").Pool(os.cpu_count()) as pool:
        return np.array(pool.map(fn, range(seed0, seed0 + n), chunksize=4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("strat"); ap.add_argument("sym"); ap.add_argument("--tf", type=int, default=5)
    ap.add_argument("--ref"); ap.add_argument("--perms", type=int, default=500)
    ap.add_argument("--all", action="store_true", help="run later gates even after a failure (diagnostic)")
    ap.add_argument("--maker", action="store_true", help="passive entry at signal close instead of taker at next open")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    fn = REG[a.strat]; grid = fn.GRID; syms = a.sym.split(","); cst = [E.cost(x) for x in syms]
    extra = dict(maker_entry=True) if a.maker else None
    name = f"{a.strat}{'-maker' if a.maker else ''}{a.tag}/{a.sym}/{a.tf}m"
    out = dict(id=name, strat=a.strat, sym=a.sym, tf=a.tf, ref=a.ref, maker=a.maker, grid_size=len(grid),
               grid_axes={k: sorted({g[k] for g in grid}) for k in grid[0]}, cost=cst, verdict=None)
    t0 = time.time()

    # ---------------- Gate 1 ----------------
    Ds = [E.load(x, a.tf, a.ref, IS_START, IS_END) for x in syms]; D = Ds[0]; yrs = len(D["c"]) / D["bpy"]
    obj, res = best_of_grid(Ds, fn, grid, cst, extra)
    i = int(obj.argmax()); r, ti, to, pn, d = res[i]
    bm = E.bar_metrics(r, D["bpy"]); tm = E.trade_metrics(ti, to, pn, d, a.tf, yrs)
    gross = eval_grid(Ds, fn, [grid[i]], [E.cost(x, 0.0) for x in syms], extra)[0]
    nb = neighbours(grid, i)
    g1 = dict(best=grid[i], **bm, **tm, gross_avg_bps=round(float(gross[3].mean() * 1e4), 2) if len(gross[3]) else None,
              gross_sharpe=round(E.sharpe(gross[0], D["bpy"]), 2), participation=E.participation(D, ti) if len(syms) == 1 else None,
              grid_share_positive=round(float((obj > 0).mean()), 3),
              neigh_med_sharpe=round(float(np.median(obj[nb])), 2) if nb else None,
              neigh_min_sharpe=round(float(obj[nb].min()), 2) if nb else None)
    fails = []
    if bm["sharpe"] < G1["sharpe"]: fails.append(f"IS Sharpe {bm['sharpe']} < {G1['sharpe']}")
    if tm["trades"] < G1["trades"]: fails.append(f"trades {tm['trades']} < {G1['trades']}")
    if tm["trades"] and (tm.get("pf_trade") or 0) < G1["pf_trade"]: fails.append(f"trade PF {tm.get('pf_trade')} < {G1['pf_trade']}")
    if bm["maxdd"] < G1["maxdd"]: fails.append(f"maxDD {bm['maxdd']}")
    if nb and g1["neigh_med_sharpe"] <= G1["neigh_med_sharpe"]: fails.append(f"no plateau: neighbour median Sharpe {g1['neigh_med_sharpe']}")
    g1["pass"] = not fails; g1["fails"] = fails; out["gate1"] = g1
    print(f"[{name}] G1 {'PASS' if g1['pass'] else 'FAIL'} {json.dumps(g1, default=str)}", flush=True)
    alive = g1["pass"]

    # ---------------- Gate 2 ----------------
    if (alive or a.all) and a.perms == 0:
        alive = False; out['note'] = 'gate-1-only run'
    elif alive or a.all:
        perm = _pool(_w2, Ds, fn, grid, cst, extra, a.perms)
        p = float(((perm >= obj[i]).sum() + 1) / (a.perms + 1))
        out["gate2"] = dict(p=round(p, 4), real=round(float(obj[i]), 2), perm_median=round(float(np.median(perm)), 2),
                            perm_p95=round(float(np.quantile(perm, .95)), 2), perm_max=round(float(perm.max()), 2),
                            n=a.perms, **{"pass": p < G2_P})
        print(f"[{name}] G2 {'PASS' if p < G2_P else 'FAIL'} {out['gate2']}", flush=True)
        alive = alive and p < G2_P

    # ---------------- Gate 3 ----------------
    if (alive or a.all) and a.perms > 0:
        Fs = [E.load(x, a.tf, a.ref) for x in syms]; F = Fs[0]
        oos, picks, tr, start = walk_forward(Fs, fn, grid, cst, extra)
        oy = len(oos) / F["bpy"]; bm3 = E.bar_metrics(oos, F["bpy"]); tm3 = E.trade_metrics(*tr, a.tf, oy)
        B = BLOCK_DAYS * F["day"]; per = {}
        for y in (2023, 2024, 2025, 2026):
            lo = max(0, int(np.searchsorted(F["t"], E._ms(f"{y}-01-01"))) - start)
            hi = max(0, int(np.searchsorted(F["t"], E._ms(f"{y + 1}-01-01"))) - start)
            if hi > lo: per[y] = dict(net=round(float(oos[lo:hi].sum()), 4), sharpe=round(E.sharpe(oos[lo:hi], F["bpy"]), 2))
        hold_lo = max(0, int(np.searchsorted(F["t"], E._ms(IS_END))) - start)
        folds = oos[:len(oos) // B * B].reshape(-1, B).sum(1)
        ok = bm3["sharpe"] >= G3_SHARPE and bm3["net"] > 0 and (tm3.get("avg_bps") or 0) > 0
        out["gate3"] = dict(**bm3, **tm3, years=round(oy, 2), by_year=per,
                            untouched_2025_26=dict(net=round(float(oos[hold_lo:].sum()), 4),
                                                   sharpe=round(E.sharpe(oos[hold_lo:], F["bpy"]), 2)),
                            folds=len(folds), folds_positive=int((folds > 0).sum()), folds_flat=int(sum(1 for x in picks if x < 0)),
                            distinct_params_used=len({x for x in picks if x >= 0}),
                            equity_by_fold=[round(float(x), 4) for x in np.cumsum(folds)], **{"pass": bool(ok)})
        print(f"[{name}] G3 {'PASS' if ok else 'FAIL'} {json.dumps({k: v for k, v in out['gate3'].items() if k != 'equity_by_fold'}, default=str)}", flush=True)
        alive = alive and ok

        # ---------------- Gate 4 ----------------
        if alive or a.all:
            perm = _pool(_w4, Fs, fn, grid, cst, extra, a.perms, start=start - 1, seed0=10_000)
            p = float(((perm >= bm3["sharpe"]).sum() + 1) / (a.perms + 1))
            out["gate4"] = dict(p=round(p, 4), real=bm3["sharpe"], perm_median=round(float(np.median(perm)), 2),
                                perm_p95=round(float(np.quantile(perm, .95)), 2), n=a.perms, **{"pass": p < G4_P})
            print(f"[{name}] G4 {'PASS' if p < G4_P else 'FAIL'} {out['gate4']}", flush=True)
            alive = alive and p < G4_P

    last = [g for g in ("gate1", "gate2", "gate3", "gate4") if g in out]
    died = next((g for g in last if not out[g]["pass"]), None)
    out["verdict"] = "SURVIVOR" if (alive and "gate4" in out) else (f"KILLED at {died}" if died else "G1 PASS - gates 2-4 not run")
    out["secs"] = round(time.time() - t0, 1); out["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    open(LOG, "a").write(json.dumps(out, default=str) + "\n")
    print(f"[{name}] => {out['verdict']} ({out['secs']}s)", flush=True)


if __name__ == "__main__":
    main()
