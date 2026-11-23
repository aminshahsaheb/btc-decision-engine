import io
import shutil
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import alerts as al  # noqa: E402

H = 3600000
NOW = 1_800_000_000_000


def make_ev(side="SHORT", ago_h=3.0):
    close_ms = int(NOW - ago_h * H)
    open_ms = close_ms - H + 1
    return {"type": "BREAK20D", "side": side, "bar_open_ms": open_ms, "close_ms": close_ms,
            "ref": 100.0, "level": 105.0, "atr": 2.0, "stop": 102.0, "target": 96.0, "note": "",
            "key": f"BREAK20D|{side}|{open_ms}"}


class Recorder:
    def __init__(self, ok=True, detail="", fail_persist_at=None):
        self.ok, self.detail, self.fail_persist_at = ok, detail, fail_persist_at
        self.sent, self.persists = [], []

    def send(self, ev):
        self.sent.append(ev["key"])
        assert len(self.persists) >= len(self.sent), "the pending row must be persisted before every send"
        return self.ok, self.detail

    def persist(self, msg):
        self.persists.append(msg)
        if self.fail_persist_at is not None and len(self.persists) == self.fail_persist_at:
            raise al.PersistError("boom")


def run(events, tmp_path, rec, v1=None, now=NOW):
    return al.process_events(events, v1 or [], tmp_path / "alerts_v2.csv", now, rec.send, rec.persist)


def states_of(tmp_path):
    return [r["state"] for r in al.read_csv(tmp_path / "alerts_v2.csv")]


def test_selftest_still_passes():
    al.selftest()


def test_success_writes_pending_then_sent_and_persists_before_send(tmp_path):
    rec = Recorder()
    s = run([make_ev()], tmp_path, rec)
    assert s["sent"] == 1 and s["uncertain"] == 0
    assert states_of(tmp_path) == ["PENDING", "SENT"]
    assert al.read_csv(tmp_path / "alerts_v2.csv")[0]["rules_version"] == "v2"
    assert len(rec.persists) == 2


def test_timeout_is_uncertain_and_never_resent(tmp_path):
    rec = Recorder(ok=False, detail="TimeoutError")
    ev = make_ev()
    s1 = run([ev], tmp_path, rec)
    assert s1["uncertain"] == 1 and rec.sent == [ev["key"]]
    s2 = run([ev], tmp_path, rec)
    assert s2["known"] == 1 and s2["sent"] == 0 and len(rec.sent) == 1
    rows = al.read_csv(tmp_path / "alerts_v2.csv")
    assert [r["state"] for r in rows] == ["PENDING", "UNCERTAIN"]
    assert "TimeoutError" in rows[-1]["note"]


def test_persist_failure_before_send_sends_nothing(tmp_path):
    rec = Recorder(fail_persist_at=1)
    with pytest.raises(al.PersistError):
        run([make_ev()], tmp_path, rec)
    assert rec.sent == []


def test_stale_event_is_logged_not_sent_and_counts_for_cooldown(tmp_path):
    old, newer = make_ev(ago_h=14.0), make_ev(ago_h=3.0)
    rec = Recorder()
    s = run([old, newer], tmp_path, rec)
    assert s["stale"] == 1 and s["suppressed"] == 1 and rec.sent == []
    assert states_of(tmp_path) == ["STALE"]


def test_other_side_is_not_suppressed(tmp_path):
    rec = Recorder()
    s = run([make_ev("SHORT", 3.0), make_ev("LONG", 2.0)], tmp_path, rec)
    assert s["sent"] == 2 and s["suppressed"] == 0


def test_stuck_pending_becomes_uncertain_and_fresh_pending_is_left_alone(tmp_path):
    ev = make_ev()
    path = tmp_path / "alerts_v2.csv"
    al.append_rows(path, [al.make_row(ev, "PENDING", NOW - 2 * H)])
    rec = Recorder()
    s = run([], tmp_path, rec)
    assert s["recovered"] == 1 and rec.sent == []
    assert al.latest_states(al.read_csv(path))[ev["key"]]["state"] == "UNCERTAIN"
    ev2 = make_ev("LONG", 3.0)
    path2 = tmp_path / "second"
    path2.mkdir()
    al.append_rows(path2 / "alerts_v2.csv", [al.make_row(ev2, "PENDING", NOW - 10 * 60000)])
    rec2 = Recorder()
    s2 = al.process_events([], [], path2 / "alerts_v2.csv", NOW, rec2.send, rec2.persist)
    assert s2["recovered"] == 0 and rec2.persists == []


def test_v1_rows_dedupe_and_count_for_cooldown(tmp_path):
    ev = make_ev("SHORT", 3.0)
    same = [{"key": ev["key"], "type": "BREAK20D", "side": "SHORT", "bar_open_ms": str(ev["bar_open_ms"])}]
    rec = Recorder()
    assert run([ev], tmp_path, rec, v1=same)["known"] == 1
    earlier = [{"key": "BREAK20D|SHORT|1", "type": "BREAK20D", "side": "SHORT",
                "bar_open_ms": str(ev["bar_open_ms"] - 18 * H)}]
    s = run([ev], tmp_path, rec, v1=earlier)
    assert s["suppressed"] == 1 and rec.sent == []


def test_message_has_age_and_warning():
    text = al.message(make_ev(ago_h=3.0), {}, NOW)
    assert "3.0 ساعت" in text and "تأییدنشده" in text
    assert "دقیقه" in al.message(make_ev(ago_h=0.5), {}, NOW)


def test_send_never_leaks_the_token(monkeypatch):
    monkeypatch.setenv("TOKEN", "SECRETTOKEN123")
    monkeypatch.setenv("CHAT", "42")

    def boom(request, timeout=None):
        raise urllib.error.HTTPError("https://api.telegram.org/botSECRETTOKEN123/sendMessage",
                                     400, "Bad Request", {}, io.BytesIO(b""))

    monkeypatch.setattr(al.urllib.request, "urlopen", boom)
    ok, detail = al.telegram_send("x")
    assert not ok and "SECRETTOKEN123" not in detail and "400" in detail


def test_send_requires_explicit_ok_true_and_uses_the_long_timeout(monkeypatch):
    monkeypatch.setenv("TOKEN", "t")
    monkeypatch.setenv("CHAT", "1")
    seen = {}

    def answer(body):
        def fake(request, timeout=None):
            seen["timeout"] = timeout
            return io.BytesIO(body)
        return fake

    monkeypatch.setattr(al.urllib.request, "urlopen", answer(b'{"ok": true}'))
    assert al.telegram_send("x")[0] is True and seen["timeout"] == al.SEND_TIMEOUT_S == 60
    monkeypatch.setattr(al.urllib.request, "urlopen", answer(b'{"ok": false}'))
    assert al.telegram_send("x")[0] is False


def test_send_without_credentials_is_not_success(monkeypatch):
    monkeypatch.delenv("TOKEN", raising=False)
    monkeypatch.delenv("CHAT", raising=False)
    assert al.telegram_send("x")[0] is False


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_persist_pushes_and_recovers_from_a_rejected_push(tmp_path, monkeypatch):
    monkeypatch.setattr(al.time, "sleep", lambda s: None)

    def g(*args, cwd=None):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    remote = tmp_path / "remote.git"
    g("init", "--bare", "-q", str(remote))
    work, other = tmp_path / "work", tmp_path / "other"
    g("clone", "-q", str(remote), str(work))
    for d in (work,):
        g("config", "user.name", "t", cwd=d)
        g("config", "user.email", "t@t", cwd=d)
    g("checkout", "-q", "-b", "alert-log", cwd=work)
    (work / "f1.txt").write_text("1")
    persist = al.make_persist(work)
    persist("first")
    g("clone", "-q", "-b", "alert-log", str(remote), str(other))
    g("config", "user.name", "t", cwd=other)
    g("config", "user.email", "t@t", cwd=other)
    (other / "f2.txt").write_text("2")
    g("add", "-A", cwd=other)
    g("commit", "-q", "-m", "second", cwd=other)
    g("push", "-q", "origin", "alert-log", cwd=other)
    (work / "f3.txt").write_text("3")
    persist("third")
    names = subprocess.run(["git", "-C", str(remote), "ls-tree", "-r", "--name-only", "alert-log"],
                           capture_output=True, text=True, check=True).stdout.split()
    assert sorted(names) == ["f1.txt", "f2.txt", "f3.txt"]
