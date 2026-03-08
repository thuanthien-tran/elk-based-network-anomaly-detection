#!/usr/bin/env python3
"""Integration test: preprocess (in-memory) -> train -> predict without Elasticsearch."""
import sys
import pandas as pd
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_preprocessing import (
    clean_data, extract_time_features, extract_ip_features,
    extract_attack_features, extract_web_features,
)
from scripts.ml_detector import NetworkAnomalyDetector


def test_pipeline_csv_to_predict():
    # Minimal SSH-like CSV in memory
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-06-01", periods=40, freq="min").astype(str),
        "source_ip": ["192.168.1.1"] * 20 + ["192.168.1.2"] * 20,
        "user": ["root"] * 40,
        "status": ["accepted"] * 25 + ["failed"] * 15,
        "is_attack": [0] * 25 + [1] * 15,
    })
    df = clean_data(df)
    df = extract_time_features(df)
    df = extract_ip_features(df)
    df = extract_attack_features(df, window_minutes=5)

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, "train.csv")
        df.to_csv(csv_path, index=False)
        model_path = os.path.join(tmp, "model.joblib")
        out_path = os.path.join(tmp, "out.csv")

        det = NetworkAnomalyDetector(model_type="random_forest")
        det.train(df, time_split=False, use_cv=False)
        det.save_model(model_path)
        out = det.predict(df)
        out.to_csv(out_path, index=False)

        assert os.path.isfile(model_path)
        assert os.path.isfile(out_path)
        assert "ml_anomaly" in out.columns
