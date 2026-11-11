from research.r2 import *
SPLIT = "2019-01-01"
vixy = load("VIXY").c; vix = load("^VIX").c; v3 = load("^VIX3M").c; spy = load("SPY").c
px = pd.concat([vixy, vix, v3, spy], axis=1, keys=["vixy","vix","v3","spy"]).dropna()
R = px.pct_change().fillna(0); ratio = px.vix/px.v3
def sv(x=0.95, cost=5, lag=0, borrow=0.05, w=1.0, start=None):
    on = (ratio < x).astype(float) if x else pd.Series(1.0, index=px.index)
    H = (-w*on).shift(1+lag).fillna(0).to_frame("vixy")
    net, held = run_w(R[["vixy"]], H, cost, borrow); return net, held
def tail(net):
    wk = (1+net).resample("W").prod()-1; mo = (1+net).resample("ME").prod()-1
    return dict(worst_day=round(net.min(),3), worst_wk=round(wk.min(),3), cvar1=round(net[net<=net.quantile(.01)].mean(),4),
                skew=round(stats.skew(net),2), mo_win=round((mo>0).mean(),3), worst_mo=round(mo.min(),3), day_win=round((net[net!=0]>0).mean(),3))
def full(lab, net, held, sl):
    n, h = net[sl], held[sl]; return {**report(lab, n, h, trades(n, h), R.spy[sl]), **tail(n)}
rows = []
for x in (None, 0.90, 0.95, 1.00):
    net, held = sv(x)
    for lab, sl in [("disc", slice(None,"2018")), ("OOS", slice(SPLIT,None))]:
        rows.append(full(f"x={x} {lab}", net, held, sl))
P(rows)
O = slice(SPLIT, None)
print("\nCost/delay x=0.95 OOS:"); P([full(f"c{c} lag{l}", *sv(0.95,c,l), O) for c in (5,10,20) for l in (0,1)])
print("\nWorst events x=0.95 (full):")
net, held = sv(0.95); print(net.nsmallest(8).round(3).to_string())
print("\nFeb-2018 / Mar-2020 / Aug-2024 windows (x=0.95):")
for s,e in [("2018-01-29","2018-02-09"),("2020-02-20","2020-03-20"),("2024-07-29","2024-08-09")]:
    print(s, e, "cum", round(np.prod(1+net[s:e])-1,3), "| unfiltered", round(np.prod(1+sv(None)[0][s:e])-1,3))
print("\nYearly return x=0.95:"); print(((1+net).groupby(net.index.year).prod()-1).round(3).to_dict())
