#!/usr/bin/env python3
"""
Offline Training Pipeline - SIEM + ML Hybrid.
Luồng: merge datasets -> clean -> feature engineering (đã có trong data) -> train RF -> save model.
Chạy: python scripts/train_model.py [--no-merge]
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from scripts.ml_detector import NetworkAnomalyDetector


def run(cmd_args, desc="", timeout=600):
    r = subprocess.run(
        [sys.executable] + cmd_args,
        cwd=str(PROJECT_ROOT),
        timeout=timeout,
    )
    return r.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Train unified SSH attack model (Offline Pipeline)")
    parser.add_argument("--no-merge", action="store_true", help="Khong gop lai, dung file unified co san")
    parser.add_argument("--unified", default=None, help="Duong dan unified CSV (mac dinh: data/training/unified_ssh_dataset.csv)")
    parser.add_argument("--model-file", "-o", default=None, help="Luu model (mac dinh: data/models/ssh_attack_model.joblib)")
    parser.add_argument("--handle-imbalance", action="store_true", default=True, help="SMOTE/balance (mac dinh: bat)")
    parser.add_argument("--no-handle-imbalance", action="store_false", dest="handle_imbalance")
    parser.add_argument("--metrics", default=None, help="Luu metrics JSON (vd: data/models/train_metrics.json)")
    args = parser.parse_args()

    unified_path = Path(args.unified) if args.unified else PROJECT_ROOT / "data" / "training" / "unified_ssh_dataset.csv"
    model_path = Path(args.model_file) if args.model_file else PROJECT_ROOT / "data" / "models" / "ssh_attack_model.joblib"
    if not unified_path.is_absolute():
        unified_path = PROJECT_ROOT / unified_path
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path

    model_path.parent.mkdir(parents=True, exist_ok=True)
    unified_path.parent.mkdir(parents=True, exist_ok=True)

    # Bước 1: Gộp dataset (trừ khi --no-merge)
    if not args.no_merge:
        print("--- Buoc 1: Gop 3 dataset (Synthetic + Russell Mitchell + Kaggle) ---")
        ok = run(
            ["scripts/merge_training_datasets.py", "--output", str(unified_path)],
            desc="merge_training_datasets",
        )
        if not ok:
            print("[LOI] Gop dataset that bai. Can it nhat 1 trong cac file sau:")
            print("  - data/processed/logs.csv (Synthetic)")
            print("  - data/processed/russellmitchell_processed.csv")
            print("  - data/processed/pipeline_ssh_processed.csv (Kaggle)")
            print("  - data/processed/custom_processed.csv (Custom, neu co)")
            return 1
    else:
        if not unified_path.exists():
            print(f"[LOI] File khong ton tai: {unified_path}. Bo --no-merge de gop truoc.")
            return 1
        print("--- Bo qua gop (--no-merge), dung file unified co san ---")

    # Bước 2: Load và clean
    print("\n--- Buoc 2: Load va clean ---")
    df = pd.read_csv(unified_path, encoding="utf-8", encoding_errors="replace", low_memory=False)
    n0 = len(df)
    df = df.drop_duplicates()
    df = df.dropna(subset=["source_ip", "status"], how="all")
    if "is_attack" in df.columns:
        df["is_attack"] = df["is_attack"].astype(bool)
    print(f"  Sau clean: {len(df)} dong (bo {n0 - len(df)} trung/thieu)")

    # Bước 3: Train Random Forest
    print("\n--- Buoc 3: Feature engineering + Train Random Forest ---")
    detector = NetworkAnomalyDetector(model_type="random_forest")
    detector.train(
        df,
        use_cv=True,
        cv_folds=5,
        handle_imbalance=args.handle_imbalance,
        metrics_output=args.metrics or str(model_path.with_suffix(".metrics.json")),
    )
    detector.save_model(str(model_path))
    print(f"\nDa luu model: {model_path}")
    print("--- Offline Training Pipeline hoan tat ---")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
