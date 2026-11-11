"""Forward (paper trading) tracking.

  python scripts/forward.py run      one analysis now
  python scripts/forward.py loop     repeat every 5 minutes until Ctrl+C
  python scripts/forward.py report   print the outcome summary
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB = ROOT / "decision_journal_v3.sqlite3"

from src.outcomes import outcome_summary  # noqa: E402
from src.scheduler import run_once  # noqa: E402


def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def cmd_run() -> None:
    info = run_once(db_path=DB)
    tag = "already stored" if info["duplicate"] else "stored"
    print(f"{stamp()} {info['label']} | candle {info['candle_time']} | {tag} | "
          f"outcomes evaluated: {info['evaluated']}")
    if info["error"]:
        print(f"  engine error (decision failed closed): {info['error']}")


def cmd_loop(seconds: int) -> None:
    print(f"{stamp()} loop started (every {seconds}s). Ctrl+C to stop.")
    while True:
        try:
            cmd_run()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"{stamp()} ERROR (nothing stored): {type(exc).__name__}: {exc}")
        time.sleep(seconds)


def cmd_report() -> None:
    s = outcome_summary(db_path=DB)
    print(f"Scheduled analyses : {s['analyses']}")
    print(f"Valid setups       : {s['setups']}")
    print(f"Pending outcomes   : {s['pending']}")
    print(f"Resolved outcomes  : {s['n_resolved']}")
    for status, v in sorted(s["by_status"].items()):
        avg = "-" if v["avg_r_net"] is None else f"{v['avg_r_net']:.3f}"
        print(f"  {status:<12} n={v['n']:<4} avg net R={avg}")
    print(f"Sum of net R (resolved): {s['sum_r_net']:.3f}")
    print("Note: a handful of trades says nothing about edge. Do not draw conclusions early.")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run")
    loop = sub.add_parser("loop")
    loop.add_argument("--seconds", type=int, default=300)
    sub.add_parser("report")
    args = parser.parse_args()
    try:
        if args.command == "run":
            cmd_run()
        elif args.command == "loop":
            cmd_loop(args.seconds)
        else:
            cmd_report()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
