#!/usr/bin/env python3
"""
Chạy luồng đầy đủ theo kiến trúc 5 tầng: Data -> SIEM -> ML -> Detection -> Response.
Tương ứng sơ đồ: Attack Simulation -> Log Collection -> Log Processing -> Storage -> ML -> Visualization -> Response.
Chạy: python scripts/run_by_architecture.py [--skip-train] [--no-browser]
"""
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

# Trên Windows (cp1252) in tiếng Việt dễ lỗi; ép stdout dùng utf-8
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(cmd_args, timeout=600):
    print("\n--- %s ---" % (" ".join(str(x) for x in cmd_args)[:70]))
    sys.stdout.flush()
    r = subprocess.run(
        [sys.executable] + [str(x) for x in cmd_args],
        cwd=str(ROOT),
        timeout=timeout,
    )
    return r.returncode == 0


def write_test_log(normal=3, attack=5):
    """Tạo test.log (Data Layer - Attack Simulation)."""
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME") or os.path.expanduser("~")
    lines = []
    for i in range(1, normal + 1):
        lines.append(
            "Jan 19 10:00:%02d localhost sshd[100%d]: Accepted password for user%d from 192.168.1.%d port 22 ssh2"
            % (i, i, i, 10 + i)
        )
    for j in range(1, attack + 1):
        lines.append(
            "Jan 19 10:01:%02d localhost sshd[20%02d]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2"
            % (j, j)
        )
    text = "\n".join(lines) + "\n"
    p = Path(user) / "Documents" / "test.log"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print("  Đã ghi test.log: %s (%d normal, %d attack)" % (p, normal, attack))
        return True
    except Exception as e:
        print("  Lỗi ghi test.log: %s" % e)
        return False


def main():
    import argparse
    p = argparse.ArgumentParser(description="Chạy luồng theo kiến trúc 5 tầng")
    p.add_argument("--skip-train", action="store_true", help="Bỏ qua train (dùng model có sẵn)")
    p.add_argument("--no-browser", action="store_true", help="Không mở Kibana")
    args = p.parse_args()

    model_path = ROOT / "data" / "models" / "ssh_attack_model.joblib"
    unified_path = ROOT / "data" / "training" / "unified_ssh_dataset.csv"
    processed_logs = ROOT / "data" / "processed" / "logs.csv"

    # ========== 1. Data Layer ==========
    print("\n=== 1. DATA LAYER (Heterogeneous Log Sources) ===")
    if not processed_logs.exists() and not args.skip_train:
        print("  Chưa có data/processed/logs.csv. Tạo Synthetic...")
        run(["scripts/generate_synthetic_logs.py", "--total", "2000", "--normal-ratio", "0.85", "--days", "7", "--replace-logs"], timeout=120)
        run(["scripts/data_preprocessing.py", "--input", "data/raw/logs.csv", "--output", "data/processed/logs.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack"], timeout=60)
    else:
        print("  Dữ liệu đã có hoặc --skip-train.")

    # ========== 2. SIEM Layer (giả định ELK đang chạy) ==========
    print("\n=== 2. SIEM LAYER (ELK Core) ===")
    print("  Đảm bảo Docker (ELK) + Filebeat đang chạy. Log sẽ qua Logstash -> Elasticsearch.")
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:9200", timeout=2)
        print("  Elasticsearch: OK")
    except Exception:
        print("  [Cảnh báo] Elasticsearch không chạy. Detection có thể dùng fallback test.log.")

    # ========== 3. ML Layer (Offline) ==========
    print("\n=== 3. ML LAYER (AI-Driven Threat Detection - Offline) ===")
    if not model_path.exists() and not args.skip_train:
        print("  Chưa có model. Train UNIFIED...")
        run(["scripts/train_model.py"], timeout=900)
    elif model_path.exists():
        print("  Model đã có: %s" % model_path.name)
    else:
        print("  --skip-train: bỏ qua train. Cần có sẵn model để Detection.")

    if not model_path.exists():
        print("[LOI] Không có model. Chạy không --skip-train hoặc train thủ công.")
        return 1

    # ========== 4. Data for Detection (Attack Simulation) ==========
    print("\n=== 4. DATA LAYER - Attack Simulation (test.log) ===")
    write_test_log(3, 5)
    print("  Nếu dùng Filebeat: đợi vài giây để Filebeat gửi log lên ES.")

    # ========== 5. Detection (ML Online + Hybrid) ==========
    print("\n=== 5. DETECTION (Hybrid: Rule-based + ML) ===")
    ok = run(["scripts/run_pipeline_detection.py"], timeout=600)
    if not ok:
        print("[LOI] Detection thất bại.")
        return 1

    # ========== 6. Response Layer ==========
    print("\n=== 6. RESPONSE LAYER (Semi-Automated) ===")
    print("  Alert: ml-alerts-* đã ghi trên Elasticsearch.")
    print("  Visualization: Kibana Discover (index ml-alerts-*).")
    print("  Suggest defense: Mở app -> Xem đề xuất phòng thủ, hoặc xem trường defense_recommendations trong Kibana.")
    if not args.no_browser:
        webbrowser.open("http://localhost:5601/app/discover#/?_a=(index:ml-alerts)")
        print("  Đã mở Kibana Discover (ml-alerts).")

    print("\n--- Luồng theo kiến trúc hoàn tất ---")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
