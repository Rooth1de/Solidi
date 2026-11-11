"""Residual-first gate (RULES.md R1)."""
import numpy as np, pandas as pd
from scipy import stats
def factor_exposure(pnl: pd.Series, factors: pd.DataFrame):
    """OLS of daily strategy P&L on factor returns. Returns betas, R^2, residual-alpha t."""
    df = pd.concat([pnl.rename("y"), factors], axis=1).dropna(); X = np.c_[np.ones(len(df)), df[factors.columns].values]
    b, *_ = np.linalg.lstsq(X, df.y.values, rcond=None); res = df.y.values - X@b
    r2 = 1 - res.var()/df.y.var(); se = np.sqrt(res.var(ddof=X.shape[1])*np.linalg.inv(X.T@X).diagonal())
    return dict(betas=dict(zip(factors.columns, np.round(b[1:], 3))), r2=round(r2, 3), alpha_t=round(b[0]/se[0], 2))
def residual_gate(trades: pd.DataFrame, daily_pnl: pd.Series, factors: pd.DataFrame, resid_panel: pd.DataFrame, ret_col="net", name_col="sym"):
    fe = factor_exposure(daily_pnl, factors)
    wk = trades[ret_col].groupby(trades.index.to_period("W")).mean(); t = stats.ttest_1samp(wk, 0).statistic
    C = resid_panel.corr().values; mpc = np.nanmean(C[np.triu_indices_from(C, 1)])
    share = trades.groupby(name_col)[ret_col].sum(); top = share.max()/share[share > 0].sum() if (share > 0).any() else np.inf
    checks = {"|beta|<0.10": all(abs(v) < 0.10 for v in fe["betas"].values()), "R2<0.10": fe["r2"] < 0.10, "resid_t>=2": t >= 2.0,
              "mean_resid_corr<0.10": mpc < 0.10, "n>=200": len(trades) >= 200, "top_name<=25%": top <= 0.25}
    return dict(factor=fe, resid_t=round(t, 2), mean_resid_corr=round(mpc, 3), top_name_share=round(top, 3), checks=checks, passed=all(checks.values()))
