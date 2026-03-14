"""
Control UI Module — CLI unified.
python -m elkshield.ui.cli --monitor | --train | --gui
"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run_cli(args=None):
    args = args or sys.argv[1:]
    p = argparse.ArgumentParser(description="ELKShield Unified Security Platform — CLI")
    p.add_argument("--monitor", action="store_true", help="Chạy Start Monitoring (flow đầy đủ)")
    p.add_argument("--train", action="store_true", help="Train UNIFIED model")
    p.add_argument("--gui", action="store_true", help="Mở GUI (dashboard)")
    p.add_argument("--no-browser", action="store_true", help="Không mở Kibana sau khi xong (dùng với --monitor)")
    a = p.parse_args(args)

    if a.gui or (not a.monitor and not a.train):
        from elkshield.ui.dashboard import run_gui
        run_gui()
        return

    if a.monitor:
        from elkshield.flow import run_monitoring_flow
        ok, msg = run_monitoring_flow(
            log_callback=lambda t, m, e: print(m),
            open_browser=not a.no_browser,
            write_test_log_first=True,
        )
        sys.exit(0 if ok else 1)

    if a.train:
        from elkshield.core.ml_engine import train_unified
        ok, out = train_unified()
        print(out or ("OK" if ok else "Lỗi"))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    run_cli()
