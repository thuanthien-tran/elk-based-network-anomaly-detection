"""
ELKShield Unified Security Platform — Entry point.
Chạy: python elkshield.py  hoặc  python -m elkshield
Sau đó: bấm Start Monitoring → tạo attack → dashboard hiện alert.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--cli", "--monitor", "--train", "--gui", "--no-browser"):
        from elkshield.ui.cli import run_cli
        run_cli()
    else:
        from elkshield.ui.dashboard import run_gui
        run_gui()


if __name__ == "__main__":
    main()
