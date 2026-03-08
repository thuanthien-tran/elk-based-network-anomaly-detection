#!/usr/bin/env python3
"""Unit tests for data_preprocessing (extract_web_features, extract_time_features)."""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.data_preprocessing import extract_web_features, extract_time_features, clean_data


def test_extract_web_features():
    df = pd.DataFrame({
        "source_ip": ["1.2.3.4", "1.2.3.4", "5.6.7.8"],
        "request": ["GET /index HTTP/1.1", "GET /page?id=1 HTTP/1.1", "POST /form HTTP/1.1"],
        "response": [200, 404, 500],
    })
    out = extract_web_features(df)
    assert "request_length" in out.columns
    assert "has_query_string" in out.columns
    assert out["has_query_string"].iloc[1] == 1
    assert out["is_4xx"].iloc[1] == 1
    assert out["is_5xx"].iloc[2] == 1
    assert "error_rate_per_ip" in out.columns


def test_extract_web_features_missing_columns():
    df = pd.DataFrame({"source_ip": ["1.2.3.4"], "other": [1]})
    out = extract_web_features(df)
    assert "request_length" in out.columns
    assert out["request_length"].iloc[0] == 0
    assert "is_4xx" in out.columns


def test_extract_time_features():
    df = pd.DataFrame({
        "timestamp": ["2025-06-15 09:00:00", "2025-06-16 14:30:00"],
    })
    out = extract_time_features(df)
    assert "hour" in out.columns
    assert "day_of_week" in out.columns
    assert "is_weekend" in out.columns
    assert out["hour"].iloc[0] == 9
    assert out["day_of_week"].iloc[0] == 6  # Sunday


def test_clean_data_dedup():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
    out = clean_data(df)
    assert len(out) == 2
