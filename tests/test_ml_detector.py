#!/usr/bin/env python3
"""Unit tests for ml_detector (prepare_features, train/predict with minimal data)."""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ml_detector import NetworkAnomalyDetector


def test_prepare_features_ssh_like():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-06-15 09:00:00", "2025-06-15 10:00:00"]),
        "source_ip": ["192.168.1.1", "192.168.1.1"],
        "user": ["root", "admin"],
        "status": ["accepted", "failed"],
    })
    det = NetworkAnomalyDetector(model_type="random_forest")
    X, df_processed = det.prepare_features(df)
    assert X.shape[0] == 2
    assert "hour" in X.columns or "requests_per_ip" in X.columns
    assert "failed_login_count" in df_processed.columns or "requests_per_ip" in df_processed.columns


def test_train_predict_random_forest():
    np.random.seed(42)
    n = 50
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=n, freq="h"),
        "source_ip": ["10.0.0.1"] * 25 + ["10.0.0.2"] * 25,
        "user": ["u1"] * 25 + ["u2"] * 25,
        "status": ["accepted"] * 30 + ["failed"] * 20,
        "is_attack": [0] * 30 + [1] * 20,
    })
    det = NetworkAnomalyDetector(model_type="random_forest")
    det.train(df, time_split=False, use_cv=False)
    out = det.predict(df)
    assert "ml_anomaly" in out.columns
    assert "ml_anomaly_score" in out.columns
    assert out["ml_anomaly"].dtype == bool or out["ml_anomaly"].dtype == np.int64


def test_train_predict_isolation_forest():
    np.random.seed(42)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=30, freq="h"),
        "source_ip": ["10.0.0.1"] * 30,
        "status": ["accepted"] * 25 + ["failed"] * 5,
    })
    det = NetworkAnomalyDetector(model_type="isolation_forest")
    det.train(df, contamination=0.2, time_split=False)
    out = det.predict(df)
    assert "ml_anomaly" in out.columns
    assert out["ml_anomaly"].sum() >= 0
