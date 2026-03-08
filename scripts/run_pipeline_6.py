#!/usr/bin/env python3
"""
Chay toan bo buoc 6 (extract -> preprocess -> train -> ghi ES) trong 1 process.
Bat moi loi, in ra man hinh, tranh crash/vo cua so.
"""
import os
import sys
import subprocess
from pathlib import Path

# Dam bao chay tu thu muc goc du an
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def run(cmd_desc, cmd_args, timeout=600):
    """Chay lenh, in output, tra ve (thanh_cong, returncode)."""
    print("\n--- %s ---" % cmd_desc)
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        r = subprocess.run(
            [sys.executable] + cmd_args,
            cwd=str(ROOT),
            timeout=timeout,
            capture_output=False,
        )
        sys.stdout.flush()
        sys.stderr.flush()
        return r.returncode == 0, r.returncode
    except subprocess.TimeoutExpired:
        print("[LOI] Timeout.")
        sys.stdout.flush()
        return False, -1
    except Exception as e:
        print("[LOI] %s" % e)
        sys.stdout.flush()
        return False, -1


def main():
    raw_csv = ROOT / "data" / "raw" / "logs.csv"
    processed_csv = ROOT / "data" / "processed" / "logs.csv"
    predictions_csv = ROOT / "data" / "predictions.csv"
    model_file = ROOT / "data" / "models" / "rf_ssh_isolation_forest.joblib"
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    processed_csv.parent.mkdir(parents=True, exist_ok=True)
    model_file.parent.mkdir(parents=True, exist_ok=True)

    # Buoc 1: Extract tu ES
    ok, _ = run(
        "Extract tu Elasticsearch",
        [
            "scripts/data_extraction.py",
            "--index", "test-logs-*,ssh-logs-*",
            "--output", str(raw_csv),
            "--hours", "8760",
            "--host", "127.0.0.1",
            "--port", "9200",
        ],
    )
    if not ok:
        # Fallback: doc tu file log
        import os
        log_path = os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "test.log")
        print("\nElasticsearch chua co log. Doc truc tiep tu: %s" % log_path)
        sys.stdout.flush()
        ok2, _ = run(
            "Doc file log -> CSV",
            ["scripts/local_log_to_csv.py", "--input", log_path, "--output", str(raw_csv)],
        )
        if not ok2:
            print("\n[LOI] Khong doc duoc file log. Chay [10] tao log truoc.")
            return 1
        print("Da doc tu file log. Tiep tuc...")
        sys.stdout.flush()

    # Buoc 2: Preprocess
    ok, _ = run(
        "Preprocess",
        [
            "scripts/data_preprocessing.py",
            "--input", str(raw_csv),
            "--output", str(processed_csv),
            "--clean", "--extract-time", "--extract-ip", "--extract-attack",
        ],
    )
    if not ok:
        print("\n[LOI] Preprocessing that bai.")
        return 1

    # Buoc 3: ML
    ok, _ = run(
        "ML (Isolation Forest)",
        [
            "scripts/ml_detector.py",
            "--input", str(processed_csv),
            "--train",
            "--model-type", "isolation_forest",
            "--model-file", str(model_file),
            "--output", str(predictions_csv),
        ],
    )
    if not ok:
        print("\n[LOI] ML that bai.")
        return 1

    # Buoc 4: Ghi ES (ml_model=isolation_forest de phan biet tren Kibana)
    ok, _ = run(
        "Ghi Elasticsearch (ml-alerts)",
        [
            "scripts/elasticsearch_writer.py",
            "--input", str(predictions_csv),
            "--index", "ml-alerts",
            "--host", "127.0.0.1",
            "--port", "9200",
            "--model-name", "isolation_forest",
        ],
    )
    if not ok:
        print("\n[LOI] Ghi ES that bai (co the ELK chua chay). Ket qua da luu CSV.")
        return 1

    print("\n--- Pipeline hoan tat. Chon [7] de mo Kibana, index: ml-alerts-* ---")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nDa dung boi nguoi dung.")
        sys.exit(130)
    except Exception as e:
        print("\n[LOI] %s" % e)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(1)
