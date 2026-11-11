# calib/ — research version of the Calibrain Harness loop (github.com/zadescoxp/calibrain-harness)
Mirrors its design on free daily data: labellable bracket question (target/stop/neither, conservative ties,
gap fills) -> walk-forward base rates (completed windows only) -> model -> blend w*model+(1-w)*base with w
fitted by Brier on PRIOR out-of-sample years -> EV_R = p_t*RR - p_s - cost/stop gate -> risk-capped book
(0.5%/trade, max 5 concurrent, 1 per symbol) -> Brier skill vs base rates, AUC, EV-decile table, traded stats.
Not runnable here from the original repo: Bybit (mainnet+testnet) and Kairos hosts are blocked; Jev
(api.typesafe.ai) is reachable but billed per token and only valid for forward (not historical) testing.
Run: `PYTHONPATH=. python3 calib/run_e1.py`
