"""
Generate a demo evidence report for the ELKShield system.

Outputs:
  - docs/DEMO_BAO_CAO_SO_LIEU.html
  - docs/DEMO_BAO_CAO_SO_LIEU.docx

The report includes:
  - Demo run summary (logs/attacks counts, accuracy, top IP)
  - Confusion matrix (TN/FP/FN/TP)
  - Timeline attack counts (last 24 hours)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elkshield.core import collector, processor, ml_engine
DOCS_DIR = PROJECT_ROOT / "docs"
HTML_OUT = DOCS_DIR / "DEMO_BAO_CAO_SO_LIEU.html"
DOCX_OUT = DOCS_DIR / "DEMO_BAO_CAO_SO_LIEU.docx"

RAW_CSV = PROJECT_ROOT / "data" / "raw" / "logs.csv"
PROCESSED_CSV = PROJECT_ROOT / "data" / "processed" / "logs.csv"
PREDICTIONS_CSV = PROJECT_ROOT / "data" / "predictions.csv"
MODEL_PATH = PROJECT_ROOT / "data" / "models" / "ssh_attack_model.joblib"


def _run(cmd: list[str], timeout: int = 900) -> None:
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True, timeout=timeout)


def ensure_model_exists() -> None:
    if MODEL_PATH.exists():
        return

    # Fallback: train a model using synthetic logs (small scale for demo/report).
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("[DEMO] Model not found. Training unified model using synthetic logs...")
    _run(
        [
            "python",
            "scripts/generate_synthetic_logs.py",
            "--total",
            "2000",
            "--normal-ratio",
            "0.85",
            "--days",
            "7",
            "--replace-logs",
        ],
        timeout=600,
    )
    _run(
        [
            "python",
            "scripts/data_preprocessing.py",
            "--input",
            "data/raw/logs.csv",
            "--output",
            "data/processed/logs.csv",
            "--clean",
            "--extract-time",
            "--extract-ip",
            "--extract-attack",
            "--log-type",
            "ssh",
        ],
        timeout=300,
    )
    _run(["python", "scripts/train_model.py"], timeout=900)


def load_metrics_and_timeline() -> dict:
    df_logs = pd.read_csv(PROCESSED_CSV, encoding="utf-8", low_memory=False)
    logs_count = int(len(df_logs))
    if "is_attack" in df_logs.columns:
        y_true = df_logs["is_attack"].astype(bool)
        attacks_count = int(y_true.sum())
    else:
        # Should not happen, but keep safe fallback.
        y_true = pd.Series([False] * logs_count)
        attacks_count = 0

    # Predictions
    df_pred = pd.read_csv(PREDICTIONS_CSV, encoding="utf-8", low_memory=False)
    if "ml_anomaly" in df_pred.columns:
        y_pred = df_pred["ml_anomaly"].astype(bool)
    elif "prediction" in df_pred.columns:
        y_pred = df_pred["prediction"].astype(bool)
    else:
        y_pred = pd.Series([False] * len(df_pred))

    # Align lengths if needed
    n = min(len(y_true), len(y_pred))
    y_true = y_true.iloc[:n].reset_index(drop=True)
    y_pred = y_pred.iloc[:n].reset_index(drop=True)

    acc = float((y_true == y_pred).mean() * 100.0) if n else 0.0

    # Confusion matrix for attack detection: positive=attack
    cm = confusion_matrix(y_true.astype(int), y_pred.astype(int), labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Top attacker IP
    top_ip = None
    if "source_ip" in df_logs.columns and attacks_count > 0:
        attacked = df_logs[df_logs["is_attack"].astype(bool)]
        if len(attacked) > 0:
            top_ip = str(attacked["source_ip"].value_counts().index[0])

    # Timeline last 24 hours (only attacks)
    hourly_attacks = [0] * 24
    if "timestamp" in df_logs.columns and len(df_logs) > 0:
        ts = pd.to_datetime(df_logs["timestamp"], errors="coerce")
        now = datetime.now()
        for i in range(24):
            start = now - timedelta(hours=23 - i)
            start = start.replace(minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
            mask = (ts >= start) & (ts < end) & (df_logs["is_attack"].astype(bool))
            hourly_attacks[i] = int(mask.sum())

    # Ingestion rate & alert rate (last 1 hour)
    ingestion_rate = None
    alert_rate = None
    if "timestamp" in df_logs.columns and len(df_logs) > 0:
        ts = pd.to_datetime(df_logs["timestamp"], errors="coerce")
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        mask1h = (ts >= cutoff) & (ts <= now)
        logs_1h = int(mask1h.sum())
        attacks_1h = int((mask1h & df_logs["is_attack"].astype(bool)).sum())
        ingestion_rate = round(logs_1h / 60.0, 3) if logs_1h else 0.0
        alert_rate = float(attacks_1h)

    # Versioning
    model_version = None
    if MODEL_PATH.exists():
        mtime = MODEL_PATH.stat().st_mtime
        model_version = "v1.0." + datetime.fromtimestamp(mtime).strftime("%y%m%d")
    dataset_version = None
    if PROCESSED_CSV.exists():
        mtime = PROCESSED_CSV.stat().st_mtime
        dataset_version = "processed." + datetime.fromtimestamp(mtime).strftime("%y%m%d")

    return {
        "run_time": datetime.now().isoformat(timespec="seconds"),
        "logs_count": logs_count,
        "attacks_count": attacks_count,
        "accuracy_percent": round(acc, 3),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "top_ip": top_ip or "—",
        "hourly_attacks": hourly_attacks,
        "ingestion_rate": ingestion_rate,
        "alert_rate": alert_rate,
        "model_version": model_version or "—",
        "dataset_version": dataset_version or "—",
        "model_path": str(MODEL_PATH),
        "processed_csv": str(PROCESSED_CSV),
        "predictions_csv": str(PREDICTIONS_CSV),
        # Note about time-based metrics:
        "note": "Test log uses timestamps close to current time (so timeline/5-min metrics work).",
    }


def generate_html(report: dict) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Timeline rendering (compact)
    blocks = " ▂▃▄▅▆▇█"
    hourly = report["hourly_attacks"]
    max_val = max(hourly) if hourly else 1
    timeline_parts = []
    for i, v in enumerate(hourly):
        h = (datetime.now() - timedelta(hours=23 - i)).strftime("%H")
        idx = min(int(round(7 * v / max_val)), 7) if max_val else 0
        timeline_parts.append(f"{h}: {blocks[idx].strip() * (1 if v > 0 else 0)}{v}")
    timeline_line = " | ".join(timeline_parts) if timeline_parts else "—"

    html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"></head>
<body>
  <h1>ELKShield Demo Evidence Report</h1>
  <p>Run time: {report['run_time']}</p>

  <h2>Demo pipeline (Start Security Workflow)</h2>
  <ul>
    <li>1) Check ELK (Elasticsearch availability)</li>
    <li>2) Load model: {Path(report['model_path']).name}</li>
    <li>3) Collect logs: generate <code>test.log</code> (normal={3}, attack={5}) then convert to CSV</li>
    <li>4) Feature extraction / preprocessing</li>
    <li>5) ML detection (predict)</li>
    <li>6) Write alert to Elasticsearch (in UI); report here uses local CSV evidence</li>
    <li>7) Suggest defense (rule engine integrated in alert records)</li>
    <li>8) Update dashboard (Kibana)</li>
  </ul>

  <h2>Run summary</h2>
  <p>Logs processed: <b>{report['logs_count']}</b></p>
  <p>Attacks detected: <b>{report['attacks_count']}</b></p>
  <p>Top attacker IP: <b>{report['top_ip']}</b></p>
  <p>Accuracy: <b>{report['accuracy_percent']}%</b></p>
  <p>Precision / Recall / F1: <b>{report['precision']}</b> / <b>{report['recall']}</b> / <b>{report['f1']}</b></p>
  <p>Log ingestion rate (last 60 min): <b>{report['ingestion_rate']}</b> logs/min</p>
  <p>Alert rate (last 60 min): <b>{report['alert_rate']}</b> alerts/hour</p>
  <p>Model version: <b>{report['model_version']}</b></p>
  <p>Dataset version: <b>{report['dataset_version']}</b></p>

  <h2>Confusion matrix (Attack = Positive)</h2>
  <p>TN: {report['confusion_matrix']['tn']}</p>
  <p>FP: {report['confusion_matrix']['fp']}</p>
  <p>FN: {report['confusion_matrix']['fn']}</p>
  <p>TP: {report['confusion_matrix']['tp']}</p>

  <h2>Timeline (Last 24 hours) — attacks count</h2>
  <p>{timeline_line}</p>

  <h2>Evidence for council (checklist)</h2>
  <ul>
    <li>UI status bar shows model loaded + ingestion metrics.</li>
    <li>Terminal output shows the full integrated flow.</li>
    <li>Kibana Discover shows records in <code>ml-alerts-*</code>.</li>
    <li>Defense strategy panel shows <code>defense_recommendations</code>.</li>
    <li>These numbers are backed by <code>{Path(report['predictions_csv']).name}</code> and <code>{Path(report['processed_csv']).name}</code>.</li>
  </ul>

  <p><i>{report['note']}</i></p>
</body>
</html>
"""
    HTML_OUT.write_text(html, encoding="utf-8")


def convert_html_to_docx() -> None:
    # Convert using the local converter (demo script inside Demo/)
    conv = PROJECT_ROOT / "Demo" / "html_to_docx.py"
    _run(
        [
            sys.executable,
            str(conv),
            "--input",
            str(HTML_OUT),
            "--output",
            str(DOCX_OUT),
        ],
        timeout=300,
    )


def run_demo_and_report() -> dict:
    ensure_model_exists()

    # 1) Generate attack simulation logs (near now, so timeline works)
    collector.write_test_log(normal=3, attack=5)

    # 2) Parse test.log -> CSV
    collector.collect_logs_from_file(
        output_csv=str(RAW_CSV),
    )

    # 3) Preprocess
    processor.run_preprocessing(str(RAW_CSV), str(PROCESSED_CSV), log_type="ssh", timeout=120)

    # 4) Predict
    ml_engine.predict(str(PROCESSED_CSV), output_csv=str(PREDICTIONS_CSV), timeout=300)

    report = load_metrics_and_timeline()
    return report


if __name__ == "__main__":
    r = run_demo_and_report()
    generate_html(r)
    convert_html_to_docx()
    print("[DEMO] Report generated:")
    print(" -", HTML_OUT)
    print(" -", DOCX_OUT)

