#!/usr/bin/env python3
"""
Đọc file log (test.log) trực tiếp và xuất CSV cùng định dạng với data_extraction.
Dùng khi Elasticsearch chưa nhận log từ Filebeat/Logstash - bước 6 vẫn chạy được.
"""
import argparse
import sys
from pathlib import Path

# Thư mục gốc dự án
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
# Import từ data_extraction (chạy từ project root: python scripts/local_log_to_csv.py)
try:
    from scripts.data_extraction import parse_ssh_message
except ImportError:
    from data_extraction import parse_ssh_message
import re
from datetime import datetime


def parse_syslog_timestamp(line):
    """Lấy phần timestamp đầu dòng và chuyển thành ISO (để preprocessing đọc được)."""
    m = re.match(r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{1,2}:\d{2}:\d{2})", line)
    if not m:
        return ""
    s = m.group(1).strip()
    try:
        year = datetime.now().year
        t = datetime.strptime(f"{s} {year}", "%b %d %H:%M:%S %Y")
        return t.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser(description="Đọc file log thành CSV (fallback khi ES không có log)")
    parser.add_argument("--input", "-i", default=None, help="Đường dẫn file log (mặc định: %%USERPROFILE%%\\Documents\\test.log)")
    parser.add_argument("--output", "-o", default="data/raw/logs.csv", help="File CSV đầu ra")
    args = parser.parse_args()

    input_path = args.input
    if not input_path:
        import os
        input_path = os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "test.log")
    input_path = Path(input_path)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    if not input_path.exists():
        print(f"[ERROR] File không tồn tại: {input_path}")
        sys.exit(1)

    rows = []
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ts_str = parse_syslog_timestamp(line)
            source_ip, user, status, is_attack, attack_type = parse_ssh_message(line)
            rows.append({
                "timestamp": ts_str,
                "source_ip": source_ip,
                "user": user,
                "status": status,
                "message": line,
                "attack_type": attack_type,
                "is_attack": is_attack,
                "geoip_country": "",
                "geoip_city": "",
                "log_type": "ssh",
            })

    if not rows:
        print(f"[ERROR] File rỗng hoặc không có dòng SSH: {input_path}")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    out_str = str(output_path)
    print(f"Da doc {len(rows)} dong tu file log -> {out_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
