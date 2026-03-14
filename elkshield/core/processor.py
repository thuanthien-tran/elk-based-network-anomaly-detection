"""
Data Processing Module — Parsing, feature engineering, aggregation.
SIEM preprocessing engine.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run(script_args, timeout=300):
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


def run_preprocessing(
    input_csv,
    output_csv=None,
    log_type="ssh",
    clean=True,
    extract_time=True,
    extract_ip=True,
    extract_attack=True,
    timeout=120,
):
    """Run data preprocessing (parsing, feature engineering)."""
    input_csv = Path(input_csv)
    if not input_csv.is_absolute():
        input_csv = ROOT / input_csv
    output_csv = output_csv or ROOT / "data" / "processed" / "logs.csv"
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "scripts/data_preprocessing.py",
        "--input", str(input_csv),
        "--output", str(output_csv),
        "--log-type", log_type,
    ]
    if clean:
        args.append("--clean")
    if extract_time:
        args.append("--extract-time")
    if extract_ip:
        args.append("--extract-ip")
    if extract_attack:
        args.append("--extract-attack")
    ok, out = _run(args, timeout=timeout)
    return ok, out, str(output_csv)
