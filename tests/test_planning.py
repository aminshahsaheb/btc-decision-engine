import pytest

from src.planning import entry_trigger, plan_trade

CFG = {
    "fee_pct_side": 0.05, "slippage_pct_side": 0.03, "min_net_rr": 1.5,
    "equity": 1000.0, "risk_pct": 0.5, "max_leverage": 2.0,
}


def test_long_trigger_true():
    assert entry_trigger("LONG", 99.0, 100.0, 101.0, 100.5, 55.0) is True


def test_long_trigger_false_when_prev_close_above_ema():
    assert entry_trigger("LONG", 101.0, 100.0, 102.0, 100.5, 55.0) is False


def test_long_trigger_false_when_rsi_not_above_50():
    assert entry_trigger("LONG", 99.0, 100.0, 101.0, 100.5, 49.0) is False


def test_short_trigger_true():
    assert entry_trigger("SHORT", 101.0, 100.0, 99.0, 99.5, 45.0) is True


def test_long_plan_numbers():
    plan = plan_trade("LONG", 100.0, 2.0, 98.0, 103.0, CFG)
    assert plan["status"] == "OK"
    assert plan["stop"] == pytest.approx(97.5)
    assert plan["risk"] == pytest.approx(2.5)
    assert plan["target1"] == pytest.approx(102.5)
    assert plan["target2"] == pytest.approx(105.0)
    assert plan["net_rr"] == pytest.approx(4.84 / 2.66)
    assert plan["quantity_estimate"] == pytest.approx(5.0 / 2.66)
    assert plan["notional_estimate"] == pytest.approx(100.0 * 5.0 / 2.66)
    assert plan["executable"] is False


def test_short_plan_numbers():
    plan = plan_trade("SHORT", 100.0, 2.0, 98.0, 102.0, CFG)
    assert plan["status"] == "OK"
    assert plan["stop"] == pytest.approx(102.5)
    assert plan["target1"] == pytest.approx(97.5)
    assert plan["target2"] == pytest.approx(95.0)
    assert plan["net_rr"] == pytest.approx(4.84 / 2.66)


def test_wide_stop_is_rejected():
    plan = plan_trade("LONG", 100.0, 2.0, 90.0, 103.0, CFG)
    assert plan["status"] == "WIDE_STOP"
    assert "quantity_estimate" not in plan


def test_low_net_rr_is_rejected():
    cfg = dict(CFG, min_net_rr=2.5)
    plan = plan_trade("LONG", 100.0, 2.0, 98.0, 103.0, cfg)
    assert plan["status"] == "LOW_NET_RR"
    assert "quantity_estimate" not in plan


def test_nan_atr_is_invalid():
    plan = plan_trade("LONG", 100.0, float("nan"), 98.0, 103.0, CFG)
    assert plan["status"] == "INVALID"


def test_unknown_side_is_invalid():
    assert plan_trade("FLAT", 100.0, 2.0, 98.0, 103.0, CFG)["status"] == "INVALID"


def test_stop_above_entry_for_long_is_invalid():
    plan = plan_trade("LONG", 100.0, 2.0, 105.0, 110.0, CFG)
    assert plan["status"] == "INVALID"


def test_quantity_capped_by_leverage():
    cfg = dict(CFG, max_leverage=0.1)
    plan = plan_trade("LONG", 100.0, 2.0, 98.0, 103.0, cfg)
    assert plan["status"] == "OK"
    assert plan["quantity_estimate"] == pytest.approx(1.0)
