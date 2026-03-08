#!/usr/bin/env python3
"""
Chay pipeline day du cho dataset SSH (Kaggle hoac CSV da chuan hoa):
  1. Chuyen doi (neu la Kaggle) -> raw CSV
  2. Preprocessing -> processed CSV
  3. Train ML (time-split) -> model + predictions + metrics JSON
Chay: python scripts/run_pipeline_ssh.py --input data/ssh_anomaly_dataset.csv [--kaggle] --output-dir data
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

def run(cmd, cwd=None):
    print(f"[RUN] {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd)
    if r.returncode != 0:
        print(f"[FAIL] exit code {r.returncode}")
        sys.exit(r.returncode)

def main():
    parser = argparse.ArgumentParser(description="Run full SSH pipeline")
    parser.add_argument("--input", required=True, help="Input: ssh_anomaly_dataset.csv (Kaggle) or already pipeline CSV")
    parser.add_argument("--kaggle", action="store_true", help="Input is Kaggle format; convert first")
    parser.add_argument("--output-dir", default="data", help="Base dir for raw/processed/models")
    parser.add_argument("--model-type", default="random_forest", choices=["random_forest", "isolation_forest", "one_class_svm"])
    parser.add_argument("--tune", action="store_true", help="GridSearchCV for RF")
    parser.add_argument("--no-time-split", action="store_true", help="Disable time-based train/test split")
    args = parser.parse_args()
    
    base = Path(args.output_dir)
    raw_dir = base / "raw"
    processed_dir = base / "processed"
    models_dir = base / "models"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    
    if args.kaggle:
        raw_csv = raw_dir / "kaggle_ssh_pipeline.csv"
        run(f'python scripts/kaggle_ssh_to_pipeline_csv.py --input "{args.input}" --output "{raw_csv}"')
        input_csv = str(raw_csv)
    else:
        input_csv = args.input
    
    proc_csv = processed_dir / "pipeline_ssh_processed.csv"
    run(f'python scripts/data_preprocessing.py --input "{input_csv}" --output "{proc_csv}" '
        f'--clean --extract-time --extract-ip --extract-attack --log-type ssh')
    
    model_file = models_dir / f"rf_ssh_{args.model_type}.joblib"
    out_csv = processed_dir / "pipeline_ssh_predictions.csv"
    metrics_file = models_dir / "metrics_ssh.json"
    time_split = "" if args.no_time_split else " --time-split --time-split-ratio 0.7"
    tune = " --tune" if args.tune and args.model_type == "random_forest" else ""
    run(f'python scripts/ml_detector.py --input "{proc_csv}" --output "{out_csv}" '
        f'--model-type {args.model_type} --train --model-file "{model_file}" '
        f'--use-cv --handle-imbalance{time_split}{tune} --metrics-output "{metrics_file}"')
    
    print("\n[DONE] Pipeline completed.")
    print(f"  Processed: {proc_csv}")
    print(f"  Model: {model_file}")
    print(f"  Predictions: {out_csv}")
    print(f"  Metrics: {metrics_file}")

if __name__ == "__main__":
    main()
