import copy
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import alerts as al  # noqa: E402
import trend_common as tc  # noqa: E402
import trend_notify as tn  # noqa: E402
import trend_state as ts  # noqa: E402

DAY = tc.DAY_MS
NOW = 1_800_000_000_000
START = 19_700 * DAY
EXTRA = ["LINKUSDT", "XLMUSDT"]


def make_rows(n, seed):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.003, 0.02, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0.0, 0.01, n))
    l = np.minimum(o, c) * (1 - rng.uniform(0.0, 0.01, n))
    return [[START + i * DAY, repr(float(o[i])), repr(float(h[i])), repr(float(l[i])), repr(float(c[i])),
             "1", 0, "1", 1, "1", "1", "0"] for i in range(n)]


@pytest.fixture(scope="module")
def tt():
    return ts.load_vendor()


@pytest.fixture(scope="module")
def market(tt):
    rows, datas = {}, {}
    for i, s in enumerate(tc.COINS + EXTRA):
        rows[s] = make_rows(400, 100 + i)
        datas[s] = tt.validate_rows(s, rows[s])
    return rows, datas


def check_against_reference(tt, market, state, asofs):
    rows, _ = market
    assert [d["asof_ms"] for d in state["days"]] == asofs
    for day, asof in zip(state["days"], asofs):
        sub = {s: tt.validate_rows(s, [r for r in rows[s] if r[0] < asof]) for s in tc.COINS}
        ref_rows, n = tt.table_rows(sub, asof)
        ref = {r["symbol"]: r for r in ref_rows}
        assert n == 7
        for r in day["rows"]:
            x = ref[r["symbol"]]
            assert r["sig"] == pytest.approx(x["sig"], abs=1e-9)
            assert r["prev_sig"] == pytest.approx(x["prev_sig"], abs=1e-9)
            assert r["w_eq"] == pytest.approx(x["w_eq"], abs=1e-12)
            assert r["close"] == pytest.approx(x["close"])
            assert r["states"] == x["states"]


def test_vendored_file_is_the_pinned_one():
    blob = ts.VENDOR.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == tc.PINNED_SHA256
    assert blob.count(b"\n") == 294


def test_load_vendor_refuses_a_modified_copy(tmp_path):
    p = tmp_path / "trendsetup.py"
    p.write_bytes(ts.VENDOR.read_bytes() + b"\n# changed\n")
    with pytest.raises(tc.StateError, match="pinned"):
        ts.load_vendor(p)


def test_first_asof_equals_the_pinned_t0(tt):
    assert tt.T0_MS == tc.FIRST_ASOF_MS
    assert tc.day_str(tc.FIRST_ASOF_MS) == "2026-11-22"


def test_slicing_equals_the_pinned_table_at_three_dates(tt, market):
    asofs = [START + k * DAY for k in (300, 330, 361)]
    state = ts.build_state(tt, market[1], asofs)
    check_against_reference(tt, market, state, asofs)
    assert any(r["sig"] > 0 for d in state["days"] for r in d["rows"])


def test_a_multi_day_gap_is_rebuilt_day_by_day(tt, market):
    asofs = [START + k * DAY for k in (350, 351, 352, 353)]
    state = ts.build_state(tt, market[1], asofs)
    check_against_reference(tt, market, state, asofs)


def test_missing_coin_is_an_error(tt, market):
    d = {k: v for k, v in market[1].items() if k != "XRPUSDT"}
    with pytest.raises(tc.StateError, match="missing"):
        ts.build_state(tt, d, [START + 330 * DAY])


def test_stale_coin_is_an_error_not_an_exit(tt, market):
    rows, datas = market
    d = dict(datas)
    d["ADAUSDT"] = tt.validate_rows("ADAUSDT", rows["ADAUSDT"][:340])
    with pytest.raises(tc.StateError, match="no bar"):
        ts.build_state(tt, d, [START + 361 * DAY])


def test_short_history_is_an_error(tt, market):
    with pytest.raises(tc.StateError, match="warm-up"):
        ts.build_state(tt, market[1], [START + 200 * DAY])


def test_plan_asofs_and_last_complete_date():
    t0 = tc.FIRST_ASOF_MS
    assert ts.plan_asofs(None, t0 + 2 * DAY) == [t0, t0 + DAY, t0 + 2 * DAY]
    assert ts.plan_asofs("2026-11-23", t0 + 3 * DAY) == [t0 + 2 * DAY, t0 + 3 * DAY]
    assert ts.plan_asofs("2026-11-25", t0 + 3 * DAY) == []
    with pytest.raises(tc.StateError):
        ts.plan_asofs(None, t0 + 100 * DAY)
    full = [{"date": "2026-11-22", "symbol": s} for s in tc.COINS]
    partial = [{"date": "2026-11-23", "symbol": "BTCUSDT"}]
    assert ts.last_complete_date(full + partial) == "2026-11-22"
    assert ts.last_complete_date([]) is None


def mkday(date, sigs=None, w_scale=1.0):
    sigs = sigs or {}
    rows = []
    for s in tc.COINS:
        sig = float(sigs.get(s, 0.0))
        rows.append({"symbol": s, "sig": sig, "prev_sig": sig, "close": 100.0,
                     "w_eq": min(1.0, sig * w_scale / 7), "data_hash": "a" * 16})
    return {"date": date, "asof_ms": tc.date_to_ms(date), "rows": rows}


class Rec:
    def __init__(self, ok=True, detail="", fail_persist_at=None):
        self.ok, self.detail, self.fail_persist_at = ok, detail, fail_persist_at
        self.texts, self.persists = [], []

    def send(self, text):
        assert self.persists, "daily rows and the pending state must be saved before the send"
        self.texts.append(text)
        return self.ok, self.detail

    def persist(self, msg):
        self.persists.append(msg)
        if self.fail_persist_at is not None and len(self.persists) == self.fail_persist_at:
            raise al.PersistError("boom")


def run(days, tmp_path, rec, now=NOW):
    return tn.run_notify(days, tmp_path, now, rec.send, rec.persist)


def test_first_run_logs_then_sends_one_message(tmp_path):
    rec = Rec()
    s = run([mkday("2026-11-22", {"BTCUSDT": 0.6, "ETHUSDT": 0.2})], tmp_path, rec)
    assert s["message"] == "SENT" and len(rec.texts) == 1 and len(rec.persists) == 2
    assert len(al.read_csv(tmp_path / "trend_daily.csv")) == 7
    assert [r["state"] for r in al.read_csv(tmp_path / "trend_msgs.csv")] == ["PENDING", "SENT"]
    assert "ENTER BTCUSDT" in rec.texts[0] and "UNPROVEN" in rec.texts[0]
    assert len(rec.texts[0]) < tn.MAX_TEXT


def test_no_change_and_volatility_only_change_send_nothing(tmp_path):
    run([mkday("2026-11-22", {"BTCUSDT": 0.6})], tmp_path, Rec())
    rec = Rec()
    s = run([mkday("2026-11-23", {"BTCUSDT": 0.6}), mkday("2026-11-24", {"BTCUSDT": 0.6}, w_scale=1.5)],
            tmp_path, rec, NOW + DAY)
    assert s["message"] == "none" and rec.texts == []
    assert len(al.read_csv(tmp_path / "trend_daily.csv")) == 21


def test_all_four_labels(tmp_path):
    run([mkday("2026-11-22", {"BTCUSDT": 0.6, "ETHUSDT": 0.2, "ADAUSDT": 0.8})], tmp_path, Rec())
    rec = Rec()
    run([mkday("2026-11-23", {"BTCUSDT": 0.4, "ETHUSDT": 0.0, "ADAUSDT": 1.0, "BNBUSDT": 0.2})],
        tmp_path, rec, NOW + DAY)
    t = rec.texts[0]
    for word in ("ENTER BNBUSDT", "ADD ADAUSDT", "REDUCE BTCUSDT", "EXIT TO CASH ETHUSDT"):
        assert word in t


def test_timeout_is_uncertain_never_resent_and_the_next_day_carries_a_note(tmp_path):
    d1 = mkday("2026-11-22", {"BTCUSDT": 0.6})
    rec = Rec(ok=False, detail="TimeoutError")
    s1 = run([d1], tmp_path, rec)
    assert s1["uncertain"] == 1 and len(rec.texts) == 1
    rec_b = Rec()
    s2 = run([d1], tmp_path, rec_b, NOW + 3_600_000)
    assert rec_b.texts == [] and s2["message"] == "none"
    rec_c = Rec()
    s3 = run([mkday("2026-11-23", {"BTCUSDT": 0.6})], tmp_path, rec_c, NOW + DAY)
    assert s3["message"] == "SENT" and "نامعلوم" in rec_c.texts[0]


def test_persist_failure_before_the_send_sends_nothing(tmp_path):
    rec = Rec(fail_persist_at=1)
    with pytest.raises(al.PersistError):
        run([mkday("2026-11-22", {"BTCUSDT": 0.6})], tmp_path, rec)
    assert rec.texts == []


def test_stuck_pending_is_recovered_as_uncertain(tmp_path):
    row = {"key": "TREND|2026-11-22", "state": "PENDING", "state_utc": al.utc_iso(NOW - 2 * 3_600_000),
           "base_date": "", "asof_date": "2026-11-22", "targets": "{}", "summary": "", "note": ""}
    tn.append_csv(tmp_path / "trend_msgs.csv", tn.MSG_FIELDS, [row])
    rec = Rec()
    s = run([], tmp_path, rec)
    assert s["recovered"] == 1 and rec.texts == []
    assert tn.latest_msgs(al.read_csv(tmp_path / "trend_msgs.csv"))["TREND|2026-11-22"]["state"] == "UNCERTAIN"


def test_daily_rows_are_deduplicated_by_date_and_symbol(tmp_path):
    d = mkday("2026-11-22", {"BTCUSDT": 0.6})
    run([d], tmp_path, Rec())
    run([d], tmp_path, Rec(), NOW + 1000)
    assert len(al.read_csv(tmp_path / "trend_daily.csv")) == 7


def test_intermediate_flips_are_listed(tmp_path):
    run([mkday("2026-11-22", {"ETHUSDT": 0.2})], tmp_path, Rec())
    days = [mkday("2026-11-23", {"ETHUSDT": 0.2}), mkday("2026-11-24", {"ETHUSDT": 0.4}),
            mkday("2026-11-25", {"ETHUSDT": 0.6})]
    rec = Rec()
    run(days, tmp_path, rec, NOW + 4 * DAY)
    assert "2026-11-24: ETHUSDT 0.2→0.4" in rec.texts[0]
    assert "ADD ETHUSDT: 0.2 → 0.6" in rec.texts[0]


def good_state():
    return {"code_sha256": tc.PINNED_SHA256, "coins": list(tc.COINS), "days": [mkday("2026-11-22", {"BTCUSDT": 0.6})]}


def test_validate_accepts_a_good_state():
    assert tc.validate_state(good_state())[0]["date"] == "2026-11-22"


def _more_days(s):
    s["days"] = [mkday("2026-11-22")] * 2


BAD = [
    lambda s: s["days"][0]["rows"][0].update(sig=0.3),
    lambda s: s["days"][0]["rows"][0].update(sig=True),
    lambda s: s["days"][0]["rows"][0].update(close=float("nan")),
    lambda s: s["days"][0]["rows"][0].update(close=-1.0),
    lambda s: s["days"][0]["rows"][0].update(w_eq=1.5),
    lambda s: s["days"][0]["rows"][0].update(symbol="DOGEUSDT"),
    lambda s: s["days"][0]["rows"][0].update(data_hash="xyz"),
    lambda s: s["days"][0].update(date="2026-13-45"),
    lambda s: s["days"][0].update(asof_ms=1),
    lambda s: s.update(code_sha256="0" * 64),
    lambda s: s.update(coins=["BTCUSDT"]),
    _more_days,
    lambda s: s.update(days=[mkday("2026-11-22")] * 61),
]


@pytest.mark.parametrize("mutate", BAD)
def test_validate_rejects_bad_states(mutate):
    s = copy.deepcopy(good_state())
    mutate(s)
    with pytest.raises(tc.StateError):
        tc.validate_state(s)


def test_validate_rejects_a_non_object():
    with pytest.raises(tc.StateError):
        tc.validate_state([])
