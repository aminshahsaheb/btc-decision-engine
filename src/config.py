"""Fixed configuration used by scheduled (forward) analyses.

The values equal the defaults in the app sidebar. They are stored in every journal record.
"""

DEFAULT_CFG = {
    "equity": 1000.0,
    "risk_pct": 0.5,
    "fee_pct_side": 0.05,
    "slippage_pct_side": 0.03,
    "max_leverage": 2.0,
    "min_net_rr": 1.5,
    "min_adx": 18.0,
    "min_volume_ratio": 0.8,
    "min_atr_pct": 0.05,
    "max_atr_pct": 1.2,
}
