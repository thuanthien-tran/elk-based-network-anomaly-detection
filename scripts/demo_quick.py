#!/usr/bin/env python3
"""
Demo nhanh: chi can Python, khong can ELK/Filebeat.
Tao du lieu mau (neu chua co) -> preprocess (neu can) -> train ML -> in ket qua + de xuat phong thu.
Chay: python scripts/demo_quick.py   (tu thu muc goc du an)
"""
import os
import sys
import subprocess
from pathlib import Path

def run(cmd, cwd=None):
    print(f"  [RUN] {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd)
    if r.returncode != 0:
        print(f"  [LOI] exit code {r.returncode}")
        return False
    return True

def main():
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    models_dir = root / "data" / "models"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Input: data/processed/logs.csv hoac data/processed/demo_logs.csv
    logs_csv = processed_dir / "logs.csv"
    demo_csv = processed_dir / "demo_logs.csv"
    
    if not logs_csv.exists():
        # Tao file mau processed (toi thieu de ML chay duoc)
        import pandas as pd
        from datetime import datetime
        now = datetime.now()
        rows = [
            {"timestamp": now, "source_ip": "10.10.10.10", "user": "admin", "status": "Failed", "message": "Failed password", "attack_type": "brute_force", "is_attack": True, "geoip_country": 0.0, "geoip_city": 0.0, "log_type": "ssh", "hour": 10, "day_of_week": 0, "day_of_month": 1, "month": 1, "is_weekend": 0, "is_business_hours": 1, "requests_per_ip": 5, "ip_hash": 12345, "failed_login_count": 5, "failed_login_count_window": 5, "attack_type_frequency": 5},
            {"timestamp": now, "source_ip": "10.10.10.10", "user": "root", "status": "Failed", "message": "Failed password", "attack_type": "brute_force", "is_attack": True, "geoip_country": 0.0, "geoip_city": 0.0, "log_type": "ssh", "hour": 10, "day_of_week": 0, "day_of_month": 1, "month": 1, "is_weekend": 0, "is_business_hours": 1, "requests_per_ip": 5, "ip_hash": 12345, "failed_login_count": 5, "failed_login_count_window": 5, "attack_type_frequency": 5},
            {"timestamp": now, "source_ip": "192.168.1.10", "user": "user1", "status": "Accepted", "message": "Accepted password", "attack_type": "", "is_attack": False, "geoip_country": 0.0, "geoip_city": 0.0, "log_type": "ssh", "hour": 10, "day_of_week": 0, "day_of_month": 1, "month": 1, "is_weekend": 0, "is_business_hours": 1, "requests_per_ip": 1, "ip_hash": 99999, "failed_login_count": 0, "failed_login_count_window": 0, "attack_type_frequency": 0},
        ]
        df = pd.DataFrame(rows)
        df.to_csv(demo_csv, index=False)
        input_csv = str(demo_csv)
        print(f"  Da tao du lieu mau: {demo_csv}")
    else:
        input_csv = str(logs_csv)
        print(f"  Dung du lieu co san: {logs_csv}")
    
    # Train + predict
    model_file = models_dir / "demo_quick_model.joblib"
    out_csv = processed_dir / "predictions_demo.csv"
    if not run(f'python scripts/ml_detector.py --input "{input_csv}" --train --model-type isolation_forest --model-file "{model_file}" --output "{out_csv}"'):
        print("Demo that bai. Kiem tra du lieu va dependencies.")
        sys.exit(1)
    
    # Doc ket qua va in de xuat phong thu
    import pandas as pd
    try:
        from scripts.defense_recommendations import get_recommendations, add_recommendations_to_dataframe
    except ImportError:
        from defense_recommendations import get_recommendations, add_recommendations_to_dataframe
    
    df = pd.read_csv(out_csv)
    n_total = len(df)
    n_anomaly = df["ml_anomaly"].astype(str).str.lower().isin(("true", "1")).sum() if "ml_anomaly" in df.columns else 0
    
    print("\n" + "=" * 50)
    print("  KET QUA DEMO NHANH")
    print("=" * 50)
    print(f"  Tong so ban ghi: {n_total}")
    print(f"  So bat thuong/tan cong (ML): {n_anomaly}")
    print("=" * 50)
    
    df = add_recommendations_to_dataframe(df)
    attack_rows = df[df["ml_anomaly"].astype(str).str.lower().isin(("true", "1"))] if "ml_anomaly" in df.columns else pd.DataFrame()
    if len(attack_rows) > 0:
        at = (attack_rows.iloc[0].get("attack_type") or "").strip() or "unknown"
        recs = get_recommendations(at, "high")
        print("\n  DE XUAT PHONG THU (loai: %s):" % at)
        for i, (title, desc) in enumerate(recs, 1):
            print(f"    %d. %s: %s" % (i, title, desc))
    else:
        print("\n  Khong phat hien ban ghi bat thuong. De xuat phong thu mau (unknown):")
        for i, (title, desc) in enumerate(get_recommendations("unknown", "medium"), 1):
            print(f"    %d. %s: %s" % (i, title, desc))
    print("\n  Hoan tat. File ket qua: %s" % out_csv)
    print("=" * 50)

if __name__ == "__main__":
    main()
