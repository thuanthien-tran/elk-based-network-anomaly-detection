#!/usr/bin/env python3
"""
Online Detection Pipeline - SIEM + ML Hybrid.
Luồng: extract logs (ES hoặc test.log) -> preprocess -> load model -> predict -> write ml-alerts.
Dùng model đã train offline (data/models/ssh_attack_model.joblib).
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MODEL = ROOT / "data" / "models" / "ssh_attack_model.joblib"
RAW_CSV = ROOT / "data" / "raw" / "logs.csv"
PROCESSED_CSV = ROOT / "data" / "processed" / "logs.csv"
PREDICTIONS_CSV = ROOT / "data" / "predictions.csv"


def run(cmd_args, timeout=600):
    print("\n--- %s ---" % (" ".join(cmd_args)[:60]))
    sys.stdout.flush()
    r = subprocess.run(
        [sys.executable] + cmd_args,
        cwd=str(ROOT),
        timeout=timeout,
    )
    return r.returncode == 0


def main():
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_MODEL.parent.mkdir(parents=True, exist_ok=True)

    if not DEFAULT_MODEL.exists():
        print("[LOI] Chua co model: %s" % DEFAULT_MODEL)
        print("  Chay train truoc: python scripts/train_model.py")
        return 1

    # 1) Extract tu ES (hoặc fallback local log)
    ok = run([
        "scripts/data_extraction.py",
        "--index", "test-logs-*,ssh-logs-*",
        "--output", str(RAW_CSV),
        "--hours", "8760",
        "--host", "127.0.0.1", "--port", "9200",
    ])
    if not ok:
        log_path = os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "test.log")
        print("Fallback: doc tu %s" % log_path)
        ok = run(["scripts/local_log_to_csv.py", "--input", log_path, "--output", str(RAW_CSV)])
        if not ok:
            print("[LOI] Khong lay duoc log. Tao test.log va bat Filebeat truoc.")
            return 1

    # 2) Preprocess
    ok = run([
        "scripts/data_preprocessing.py",
        "--input", str(RAW_CSV),
        "--output", str(PROCESSED_CSV),
        "--clean", "--extract-time", "--extract-ip", "--extract-attack",
    ])
    if not ok:
        return 1

    # 3) Load model + predict (không train)
    ok = run([
        "scripts/ml_detector.py",
        "--input", str(PROCESSED_CSV),
        "--model-file", str(DEFAULT_MODEL),
        "--output", str(PREDICTIONS_CSV),
    ])
    if not ok:
        return 1

    # 4) Ghi ml-alerts (ml_model=unified de phan biet tren Kibana)
    ok = run([
        "scripts/elasticsearch_writer.py",
        "--input", str(PREDICTIONS_CSV),
        "--index", "ml-alerts",
        "--host", "127.0.0.1", "--port", "9200",
        "--model-name", "unified",
    ])
    if not ok:
        print("[Canh bao] Khong ghi duoc ES. Ket qua da luu: %s" % PREDICTIONS_CSV)

    print("\n--- Online Detection Pipeline xong. Kibana: ml-alerts-* ---")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
