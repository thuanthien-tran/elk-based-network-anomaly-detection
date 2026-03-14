#!/usr/bin/env python3
"""
Response Layer - Auto mitigation (future work).
Placeholder: nhận danh sách IP từ alert, (sẽ) gọi firewall/API block.
Chạy: python scripts/response/auto_mitigation_stub.py --ip 1.2.3.4 [--dry-run]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser(description="Auto mitigation stub - block IP (future: firewall/IDS)")
    p.add_argument("--ip", action="append", default=[], help="IP to block (có thể lặp)")
    p.add_argument("--dry-run", action="store_true", help="Chỉ in, không thực hiện")
    args = p.parse_args()
    if not args.ip:
        print("Chưa triển khai: cần --ip. Future: đọc IP từ ml-alerts rồi gọi firewall/API.")
        return 0
    if args.dry_run:
        print("[DRY-RUN] Sẽ block IP:", ", ".join(args.ip))
        print("Future: tích hợp firewall / IDS / SOAR.")
        return 0
    print("Auto block chưa triển khai. Dùng --dry-run để xem. Future: firewall integration.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
