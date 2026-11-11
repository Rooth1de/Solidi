# quant/ research harness
- `data/fetch.py` Yahoo v8 daily fetch (CSV cache, gitignored). Survivorship caveat: ETF universe is current-listed.
- `research/engine.py` signals, backtester (lag/cost aware), trade stats, beta-adjusted alpha, Deflated Sharpe, experiment logger.
- `research/h1_run.py` frozen-param disc/OOS; `research/h1_stress.py` cost, delay, cross-asset, random-timing null, shuffled-bar null, sweeps, concentration.
- `logs/experiments.jsonl` every experiment; `logs/DEAD_STRATEGIES.md` rejected list.
Run: `pip install numpy pandas scipy; cd quant/data && python fetch.py SPY QQQ ...; cd ..; python research/h1_stress.py`
Known limits: no intraday data, no options/vol data, no point-in-time single-stock universe, lag0 assumes MOC fill at an unknowable close.
