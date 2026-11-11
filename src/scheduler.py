from __future__ import annotations

from src.config import DEFAULT_CFG
from src.data import load_all
from src.decision import decide
from src.journal import input_fingerprint, save_analysis
from src.outcomes import evaluate_pending


def run_once(load=None, db_path=None, cfg=None) -> dict:
    """Fetch data, decide, store one record per closed 15m candle, then evaluate pending setups.

    If fetching or validation raises, nothing is stored (the error propagates).
    """
    load = load or load_all
    cfg = dict(DEFAULT_CFG if cfg is None else cfg)
    market, deriv = load()
    result = decide(market, deriv, cfg)
    candle_time = str(market["15m"]["time"].iloc[-1])
    saved = save_analysis(
        result, cfg, input_fingerprint(market, deriv, cfg),
        db_path=db_path, candle_time=candle_time, source="scheduled",
    )
    evaluated = evaluate_pending(market["15m"], db_path=db_path)
    return {
        "label": result["label"],
        "candle_time": candle_time,
        "duplicate": saved["duplicate"],
        "analysis_id": saved["id"],
        "evaluated": evaluated,
        "error": result.get("error"),
    }
