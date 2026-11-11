"""Engine sanity checks: accounting identities, look-ahead guard, permutation invariants."""
import numpy as np, engine as E
D = E.load("BTCUSDT", 5, start="2024-01-01", end="2024-03-01"); n = len(D["c"])
# 1) always-long, never exits, zero cost, no funding == buy & hold from the first fill
D0 = dict(D); D0["fund"] = np.zeros(n)
r, ti, to, pn, d = E.run(D0, dict(sig=np.ones(n), max_hold=10**9), E.cost("BTCUSDT", 0.0))
assert abs(np.prod(1 + r) - D["c"][-1] / D["o"][1]) < 1e-9, "buy&hold identity"
# 2) round-trip cost: enter every other bar, hold 1 bar -> cost per trade = 2*(fee+slip) exactly (to 1st order)
sig = np.zeros(n); sig[:-4:2] = 1            # leave no trade open at the end
c0 = E.run(D0, dict(sig=sig, max_hold=1), E.cost("BTCUSDT", 0.0)); c1 = E.run(D0, dict(sig=sig, max_hold=1), E.cost("BTCUSDT"))
per = (c0[3].mean() - c1[3].mean()) * 1e4
assert abs(per - 12.0) < 0.05, per
assert abs(c1[0].sum() - c1[3].sum()) < 1e-9, "bar returns must sum to trade pnl"
# 3) look-ahead guard: a signal that peeks at the NEXT bar must be hugely profitable, the lagged one must not
peek = np.sign(np.concatenate((np.diff(np.log(D["c"])), [0])))
a = E.run(D0, dict(sig=peek, max_hold=1), E.cost("BTCUSDT"))[3].mean() * 1e4
b = E.run(D0, dict(sig=np.roll(peek, 1), max_hold=1), E.cost("BTCUSDT"))[3].mean() * 1e4
print(f"per-trade net bps  peeking={a:.1f}  honest-lagged={b:.1f}  cost/round-trip={per:.2f}")
assert b < 0 < a or a < 0   # peeking at close[t+1] while filling at open[t+1] ~ open-to-close of t+1
# 4) funding: flat price, long through one settlement pays exactly the rate
F = dict(D0); 
for k in "ohlc": F[k] = np.full(n, 100.0)
F["fund"] = np.zeros(n); F["fund"][50] = 0.0003
x = E.run(F, dict(sig=np.r_[np.zeros(40), 1, np.zeros(n - 41)], max_hold=20), E.cost("BTCUSDT", 0.0))
assert abs(x[3][0] + 0.0003) < 1e-12, x[3]
# 5) permutation: same multiset of bar returns, same terminal price, structure gone
P = E.permute(D, 1)
assert abs(P["c"][-1] / D["c"][-1] - 1) < 1e-9
assert np.allclose(np.sort(np.log(P["c"] / P["o"])[1:]), np.sort(np.log(D["c"] / D["o"])[1:]))
assert (P["h"] >= np.maximum(P["o"], P["c"]) - 1e-9).all() and (P["l"] <= np.minimum(P["o"], P["c"]) + 1e-9).all()
ac = lambda x: np.corrcoef(np.abs(x[1:]), np.abs(x[:-1]))[0, 1]
print(f"|ret| autocorr real={ac(np.diff(np.log(D['c']))):.3f} permuted={ac(np.diff(np.log(P['c']))):.3f}")
Q = E.permute(D, 1, start=5000); assert np.array_equal(Q["c"][:5001], D["c"][:5001]) and not np.array_equal(Q["c"], D["c"])
print("selftest OK")
