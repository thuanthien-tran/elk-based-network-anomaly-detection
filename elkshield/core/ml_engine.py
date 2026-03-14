"""
ML Engine Module — Training, prediction, model management.
AI detection engine.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MODEL = ROOT / "data" / "models" / "ssh_attack_model.joblib"


def _run(script_args, timeout=600):
    import subprocess
    r = subprocess.run(
        [sys.executable] + list(script_args),
        cwd=str(ROOT),
        timeout=timeout,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return r.returncode == 0, (r.stdout or "") + (r.stderr or "")


def load_model(model_path=None):
    """Check if model exists and return path."""
    p = Path(model_path or DEFAULT_MODEL)
    if not p.is_absolute():
        p = ROOT / p
    return str(p) if p.exists() else None


def train_unified(timeout=900):
    """Train unified model (merge datasets + train RF)."""
    ok, out = _run(["scripts/train_model.py"], timeout=timeout)
    return ok, out


def predict(processed_csv, model_path=None, output_csv=None, timeout=300):
    """Run ML detection (load model, predict, output CSV)."""
    model_path = model_path or DEFAULT_MODEL
    model_path = ROOT / model_path if not Path(model_path).is_absolute() else Path(model_path)
    output_csv = output_csv or ROOT / "data" / "predictions.csv"
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    processed_csv = Path(processed_csv)
    if not processed_csv.is_absolute():
        processed_csv = ROOT / processed_csv
    ok, out = _run([
        "scripts/ml_detector.py",
        "--input", str(processed_csv),
        "--model-file", str(model_path),
        "--output", str(output_csv),
    ], timeout=timeout)
    return ok, out, str(output_csv)
