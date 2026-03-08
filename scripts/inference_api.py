#!/usr/bin/env python3
"""
REST API cho inference real-time: load model, nhan batch log -> tra ve is_attack, score.
Bao mat: API key (env ELKSHIELD_API_KEY hoac --api-key) hoac Basic auth (--basic-auth user:password).
Chay: python scripts/inference_api.py --model-file data/models/ssh_attack_model.joblib [--port 5000] [--api-key xxx]
Goi: POST /predict voi JSON { "records": [ {"source_ip": "...", "timestamp": "...", "user": "...", "status": "..." }, ... ] }
     Header: X-API-Key: <key> hoac Authorization: Basic <base64(user:password)>
     Tra ve: { "predictions": [ {"is_attack": true, "ml_anomaly_score": 0.95}, ... ] }
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import joblib


def load_detector(model_file):
    data = joblib.load(model_file)
    from scripts.ml_detector import NetworkAnomalyDetector
    det = NetworkAnomalyDetector(model_type=data["model_type"])
    det.model = data["model"]
    det.scaler = data["scaler"]
    det.label_encoders = data.get("label_encoders", {})
    det.threshold = data.get("threshold")
    det.model_type = data.get("model_type", det.model_type)
    return det


def _check_auth(api_key=None, basic_auth=None):
    """Validate request: X-API-Key or Authorization Basic. Return (ok, error_message)."""
    from flask import request
    if not api_key and not basic_auth:
        return True, None
    # API key
    if api_key:
        key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if key == api_key:
            return True, None
        if key:
            return False, "Invalid API key"
        return False, "Missing X-API-Key or Authorization: Bearer <key>"
    # Basic auth: (user, password) tuple
    if basic_auth:
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Basic "):
            return False, "Missing Authorization: Basic"
        try:
            decoded = base64.b64decode(auth[6:].strip()).decode("utf-8")
            user, _, password = decoded.partition(":")
            if (user, password) == basic_auth:
                return True, None
        except Exception:
            pass
        return False, "Invalid Basic auth"


def main():
    parser = argparse.ArgumentParser(description="ELKShield Inference API")
    parser.add_argument("--model-file", required=True, help="Path to .joblib model")
    parser.add_argument("--port", type=int, default=5000, help="Port")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--api-key", default=os.environ.get("ELKSHIELD_API_KEY"), help="API key for /predict (or set ELKSHIELD_API_KEY)")
    parser.add_argument("--basic-auth", metavar="USER:PASSWORD", help="Basic auth for /predict (e.g. admin:secret)")
    args = parser.parse_args()

    api_key = args.api_key
    basic_auth = None
    if args.basic_auth:
        u, _, p = args.basic_auth.partition(":")
        if not u or not p:
            print("[ERROR] --basic-auth must be USER:PASSWORD")
            sys.exit(1)
        basic_auth = (u, p)

    if not Path(args.model_file).is_file():
        print(f"[ERROR] Model file not found: {args.model_file}")
        sys.exit(1)

    print(f"Loading model from {args.model_file}...")
    detector = load_detector(args.model_file)
    print("Model loaded.")

    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Install Flask: pip install flask")
        sys.exit(1)

    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/predict", methods=["POST"])
    def predict():
        if api_key or basic_auth:
            ok, err = _check_auth(api_key, basic_auth)
            if not ok:
                return jsonify({"error": err}), 401
        try:
            body = request.get_json(force=True, silent=True) or {}
            records = body.get("records", [])
            if not records:
                return jsonify({"error": "Missing or empty 'records'"}), 400
            df = pd.DataFrame(records)
            # Ensure required columns for pipeline
            for col in ["source_ip", "timestamp"]:
                if col not in df.columns:
                    df[col] = ""
            if "user" not in df.columns:
                df["user"] = ""
            if "status" not in df.columns:
                df["status"] = ""

            out = detector.predict(df)
            try:
                from scripts.defense_recommendations import get_recommendations
            except ImportError:
                try:
                    from defense_recommendations import get_recommendations
                except ImportError:
                    get_recommendations = None
            predictions = []
            for _, row in out.iterrows():
                is_attack = bool(row.get("ml_anomaly", False))
                pred = {
                    "is_attack": is_attack,
                    "ml_anomaly_score": float(row.get("ml_anomaly_score", 0.0)),
                }
                if get_recommendations:
                    attack_type = (row.get("attack_type") or "").strip() or "unknown"
                    severity = "high" if is_attack else "medium"
                    recs = get_recommendations(attack_type, severity)
                    pred["defense_recommendations"] = [{"title": t, "description": d} for t, d in recs]
                predictions.append(pred)
            return jsonify({"predictions": predictions})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    print(f"Starting API on http://{args.host}:{args.port}")
    print("  GET /health  - health check")
    print("  POST /predict - body: {\"records\": [{...}, ...]}")
    if api_key:
        print("  Auth: API key required (X-API-Key or Authorization: Bearer)")
    elif basic_auth:
        print("  Auth: Basic auth required")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
