#!/usr/bin/env python3
"""
Gộp 3 dataset SSH (Synthetic, Russell Mitchell, Kaggle) đã qua preprocess
thành unified training dataset. Chuẩn hóa cột (bỏ host, thêm geoip nếu thiếu).
SIEM + ML Hybrid - Offline Training Pipeline.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Cột chuẩn sau preprocess (theo data_preprocessing + ml_detector)
STANDARD_COLS = [
    "timestamp", "source_ip", "user", "status", "message",
    "attack_type", "is_attack", "geoip_country", "geoip_city", "log_type",
    "hour", "day_of_week", "day_of_month", "month",
    "is_weekend", "is_business_hours",
    "requests_per_ip", "ip_hash",
    "failed_login_count", "failed_login_count_window", "attack_type_frequency",
]


def normalize_df(df):
    """Chuẩn hóa DataFrame: bỏ cột thừa (host), thêm cột thiếu (geoip)."""
    out = df.copy()
    if "host" in out.columns:
        out = out.drop(columns=["host"])
    for col in STANDARD_COLS:
        if col not in out.columns:
            if col in ("geoip_country", "geoip_city"):
                out[col] = 0.0
            else:
                out[col] = None
    # Chỉ giữ cột có trong STANDARD_COLS
    cols = [c for c in STANDARD_COLS if c in out.columns]
    out = out[cols].copy()
    out["geoip_country"] = pd.to_numeric(out["geoip_country"], errors="coerce").fillna(0)
    out["geoip_city"] = pd.to_numeric(out["geoip_city"], errors="coerce").fillna(0)
    if "is_attack" in out.columns:
        out["is_attack"] = out["is_attack"].fillna(False)
        out["is_attack"] = out["is_attack"].astype(bool)
    return out


def main():
    parser = argparse.ArgumentParser(description="Gộp 3 dataset SSH thành unified training dataset")
    parser.add_argument("--synthetic", default=None,
                        help="CSV đã preprocess từ Synthetic (mặc định: data/processed/logs.csv)")
    parser.add_argument("--russell", default=None,
                        help="CSV đã preprocess từ Russell Mitchell (mặc định: data/processed/russellmitchell_processed.csv)")
    parser.add_argument("--kaggle", default=None,
                        help="CSV đã preprocess từ Kaggle (mặc định: data/processed/pipeline_ssh_processed.csv)")
    parser.add_argument("--output", "-o", default=None,
                        help="Unified CSV (mặc định: data/training/unified_ssh_dataset.csv)")
    args = parser.parse_args()

    root = PROJECT_ROOT
    synthetic_path = Path(args.synthetic) if args.synthetic else root / "data" / "processed" / "logs.csv"
    russell_path = Path(args.russell) if args.russell else root / "data" / "processed" / "russellmitchell_processed.csv"
    kaggle_path = Path(args.kaggle) if args.kaggle else root / "data" / "processed" / "pipeline_ssh_processed.csv"
    out_path = Path(args.output) if args.output else root / "data" / "training" / "unified_ssh_dataset.csv"
    if not out_path.is_absolute():
        out_path = root / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    names = []

    for path, name in [
        (synthetic_path, "Synthetic"),
        (russell_path, "Russell Mitchell"),
        (kaggle_path, "Kaggle"),
    ]:
        if not path.exists():
            print(f"[SKIP] Khong tim thay: {path} ({name})")
            continue
        try:
            df = pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
            df = normalize_df(df)
            df["_source"] = name
            frames.append(df)
            names.append(name)
            print(f"  + {name}: {len(df)} dong")
        except Exception as e:
            print(f"[LOI] Doc {path}: {e}")
            sys.exit(1)

    if not frames:
        print("[LOI] Khong co file nao de gop. Chay preprocess cho tung nguon truoc.")
        sys.exit(1)

    unified = pd.concat(frames, ignore_index=True)
    unified = unified.drop(columns=["_source"], errors="ignore")
    # Sắp xếp theo thời gian nếu có
    if "timestamp" in unified.columns:
        unified["timestamp"] = pd.to_datetime(unified["timestamp"], errors="coerce")
        unified = unified.sort_values("timestamp").reset_index(drop=True)
    unified.to_csv(out_path, index=False)
    n_attack = unified["is_attack"].sum() if "is_attack" in unified.columns else 0
    print(f"\nDa gop {len(unified)} dong -> {out_path}")
    print(f"  Normal: {len(unified) - n_attack}, Attack: {n_attack}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
