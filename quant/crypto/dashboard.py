"""Build quant/logs/CRYPTO_DASHBOARD.md from crypto_experiments.jsonl (latest run per id)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); LOGS = os.path.join(HERE, "..", "logs")
runs = {}
for l in open(os.path.join(LOGS, "crypto_experiments.jsonl")):
    o = json.loads(l); runs[o["id"]] = o
def depth(o): return sum(1 for g in ("gate1", "gate2", "gate3", "gate4") if o.get(g, {}).get("pass"))
def score(o):                       # robustness x expectancy: gates cleared, then OOS Sharpe x OOS net bps/trade
    g3 = o.get("gate3", {})
    return (depth(o), (g3.get("sharpe") or -9) * max(g3.get("avg_bps") or 0, 0), o["gate1"]["sharpe"])
def verdict(o):
    if depth(o) == 4: return "SURVIVOR"
    died = next((g for g in ("gate1", "gate2", "gate3", "gate4") if g in o and not o[g]["pass"]), None)
    return f"KILLED at {died}" if died else f"ALIVE - passed gate {depth(o)}, next gate pending"
def why(o):
    for g in ("gate1", "gate2", "gate3", "gate4"):
        x = o.get(g)
        if x is None: return "awaiting next gate"
        if not x["pass"]:
            if g == "gate1": return "; ".join(x["fails"])
            if g == "gate2": return f"noise does as well: p={x['p']} (real {x['real']} vs perm p95 {x['perm_p95']})"
            if g == "gate3": return f"walk-forward OOS Sharpe {x['sharpe']}, net {x['net']}, {x.get('avg_bps')}bp/trade; 2025-26 net {x['untouched_2025_26']['net']}"
            return f"OOS not distinguishable from permuted OOS: p={x['p']}"
    return "passed all four"
rows = sorted(runs.values(), key=score, reverse=True)
L = ["# Crypto intraday research dashboard", "",
     "Engine: `quant/crypto/engine.py` (deterministic; taker 5bp / maker 2bp per side, slippage 1bp BTC/ETH, 2bp alts, funding at settlement).",
     "Data: Binance USD-M perps, 1m klines 2023-01..2026-10. Gate 1/2 in-sample = 2023-2024; walk-forward = 180d train / 30d trade; 2025-26 never used for idea selection.",
     "Ranking: gates cleared, then walk-forward Sharpe x net bp/trade.", "",
     "| # | Candidate | Symbols | TF | G1 Sharpe | G1 trades | G1 win | G1 net/gross bp | G2 p | G3 OOS Sharpe | G3 net bp | G3 win | G4 p | Verdict | Precise reason |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for k, o in enumerate(rows, 1):
    c, sy, tf = o["id"].split("/"); g1 = o["gate1"]; g2 = o.get("gate2", {}); g3 = o.get("gate3", {}); g4 = o.get("gate4", {})
    sy = "pool-6" if sy.count(",") == 5 else sy.replace("USDT", "")
    L.append(f"| {k} | {c} | {sy} | {tf} | {g1['sharpe']} | {g1['trades']} | {g1.get('win', '-')} | {g1.get('avg_bps', '-')} / {g1.get('gross_avg_bps', '-')} | "
             f"{g2.get('p', '-')} | {g3.get('sharpe', '-')} | {g3.get('avg_bps', '-')} | {g3.get('win', '-')} | {g4.get('p', '-')} | **{verdict(o)}** | {why(o)} |")
L += ["", f"Total candidates: {len(rows)} | survivors: {sum(verdict(o) == 'SURVIVOR' for o in rows)} | "
          f"parameter sets evaluated: {sum(o['grid_size'] for o in rows)}", ""]
open(os.path.join(LOGS, "CRYPTO_DASHBOARD.md"), "w").write("\n".join(L))
print("\n".join(L))
