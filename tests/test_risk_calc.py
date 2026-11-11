import pytest

from src.risk_calc import position_size


def calc(side="LONG", entry=100.0, stop=97.5, **kw):
    args = dict(equity=1000.0, risk_pct=0.5, fee_pct_side=0.05,
                slippage_pct_side=0.03, max_leverage=2.0)
    args.update(kw)
    return position_size(side, entry, stop, **args)


def test_long_numbers():
    r = calc()
    assert r["status"] == "OK"
    assert r["quantity_estimate"] == pytest.approx(5.0 / 2.66)
    assert r["notional_estimate"] == pytest.approx(100.0 * 5.0 / 2.66)
    assert r["risk_cash_estimate"] == pytest.approx(5.0)
    assert r["cost_estimate"] == pytest.approx(0.16)
    assert r["stop_pct"] == pytest.approx(2.5)
    assert r["target_1r"] == pytest.approx(102.5)
    assert r["target_2r"] == pytest.approx(105.0)
    assert r["target_3r"] == pytest.approx(107.5)
    assert r["warnings"] == []
    assert r["executable"] is False


def test_short_numbers():
    r = calc(side="SHORT", stop=102.5)
    assert r["status"] == "OK"
    assert r["quantity_estimate"] == pytest.approx(5.0 / 2.66)
    assert r["target_1r"] == pytest.approx(97.5)
    assert r["target_2r"] == pytest.approx(95.0)
    assert r["target_3r"] == pytest.approx(92.5)


def test_leverage_cap_reduces_quantity_and_warns():
    r = calc(max_leverage=0.1)
    assert r["quantity_estimate"] == pytest.approx(1.0)
    assert r["risk_cash_estimate"] == pytest.approx(2.66)
    assert "LEVERAGE_CAPPED" in r["warnings"]


def test_wide_stop_warns():
    r = calc(stop=90.0)
    assert r["status"] == "OK"
    assert "WIDE_STOP" in r["warnings"]


@pytest.mark.parametrize("side,entry,stop", [
    ("LONG", 100.0, 100.0),
    ("LONG", 100.0, 105.0),
    ("SHORT", 100.0, 95.0),
    ("FLAT", 100.0, 97.0),
    ("LONG", 0.0, 97.0),
    ("LONG", 100.0, 0.0),
    ("LONG", float("nan"), 97.0),
])
def test_invalid_inputs(side, entry, stop):
    r = calc(side=side, entry=entry, stop=stop)
    assert r["status"] == "INVALID"
    assert r["executable"] is False


def test_invalid_risk_and_equity():
    assert calc(risk_pct=0.0)["status"] == "INVALID"
    assert calc(equity=-5.0)["status"] == "INVALID"
    assert calc(fee_pct_side=-0.1)["status"] == "INVALID"
