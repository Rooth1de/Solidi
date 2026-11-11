"""Reconstruct what the process displayed on a past date: `python -m timemachine.reviewer RUN YYYY-MM-DD`."""
import sys, sqlite3, json, pandas as pd
from timemachine.core import DB
def show(run, date):
    con = sqlite3.connect(DB)
    s = pd.read_sql("SELECT sym, payload, signal, action FROM scans WHERE run=? AND date=?", con, params=(run, date))
    r = pd.read_sql("SELECT * FROM regimes WHERE date=?", con, params=(date,))
    t = pd.read_sql("SELECT sym, side, entry, exit, net FROM trades WHERE run=? AND date=?", con, params=(run, date)); con.close()
    print(f"=== {run} as seen on {date} === regime: {r.to_dict('records')}")
    if len(s): print(pd.concat([s[["sym","signal","action"]], pd.json_normalize(s.payload.map(json.loads))], axis=1).to_string(index=False))
    print("trades opened (outcome filled later by the executor):"); print(t.to_string(index=False) if len(t) else "  none")
if __name__ == "__main__": show(sys.argv[1], sys.argv[2])
