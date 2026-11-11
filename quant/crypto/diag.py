"""Fixed-parameter robustness diagnostics (NOT a gate; used to stress survivors and understand near-misses).
Usage: python diag.py <strategy> <SYM,SYM..> <tf> '<json params>' [--maker]"""
import sys, json
import numpy as np
import engine as E
from strategies import REG

def book(Ds, fn, p, mult=1.0, delay=0, maker=False):
    parts = []
    for D in Ds:
        spec = fn(D, p)
        if delay: spec["sig"] = np.concatenate((np.zeros(delay, np.int8), spec["sig"][:-delay])); \
                  spec["sl"] = None if spec.get("sl") is None else np.concatenate((np.zeros(delay), spec["sl"][:-delay]))
        if maker: spec["maker_entry"] = True
        parts.append(E.run(D, spec, E.cost(D["sym"], mult)))
    return parts

def line(tag, parts, D, lo=0, hi=None):
    hi = hi or len(D["c"]); r = sum(x[0][lo:hi] for x in parts) / len(parts)
    w = [(x[1] >= lo) & (x[1] < hi) for x in parts]
    pn = np.concatenate([x[3][m] for x, m in zip(parts, w)])
    n = len(pn)
    print(f"  {tag:26s} trades {n:5d}  win {np.mean(pn > 0) if n else 0:5.3f}  net/trade {pn.mean() * 1e4 if n else 0:7.2f}bp  "
          f"t {pn.mean() / pn.std() * np.sqrt(n) if n > 2 else 0:5.2f}  book net {r.sum():7.4f}  Sharpe {E.sharpe(r, D['bpy']):5.2f}")

if __name__ == "__main__":
    st, syms, tf, p = sys.argv[1], sys.argv[2].split(","), int(sys.argv[3]), json.loads(sys.argv[4]); maker = "--maker" in sys.argv
    fn = REG[st]; Ds = [E.load(s, tf) for s in syms]; D = Ds[0]
    base = book(Ds, fn, p, maker=maker)
    print(f"{st} {p} maker={maker} | full sample 2023-01..2026-10, fixed parameters")
    line("ALL", base, D)
    for y in (2023, 2024, 2025, 2026):
        lo = int(np.searchsorted(D["t"], E._ms(f"{y}-01-01"))); hi = int(np.searchsorted(D["t"], E._ms(f"{y + 1}-01-01")))
        line(str(y), base, D, lo, hi)
    for s, x, d in zip(syms, base, Ds): line(s, [x], d)
    for sd, nm in ((1, "long only"), (-1, "short only")):
        line(nm, [(np.zeros(1), x[1][x[4] == sd], x[2][x[4] == sd], x[3][x[4] == sd], x[4][x[4] == sd]) for x in base], D)
    for m in (0.0, 1.5, 2.0, 3.0): line(f"costs x{m}", book(Ds, fn, p, m, maker=maker), D)
    for dl in (1, 2): line(f"entry delayed {dl} bar(s)", book(Ds, fn, p, delay=dl, maker=maker), D)
