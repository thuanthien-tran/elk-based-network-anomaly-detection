"""
Data Collector Module — Collect logs realtime, load dataset offline.
Filebeat / Log ingestion / Dataset loader.
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run(script_args, timeout=600, cwd=None):
    cwd = cwd or str(ROOT)
    r = subprocess.run(
        [sys.executable] + list(script_args),
        cwd=cwd,
        timeout=timeout,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return r.returncode == 0, (r.stdout or "") + (r.stderr or "")


def collect_logs_from_es(host="127.0.0.1", port=9200, index="test-logs-*,ssh-logs-*", hours=8760, output_csv=None):
    """Collect logs from Elasticsearch (log ingestion)."""
    output_csv = output_csv or ROOT / "data" / "raw" / "logs.csv"
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    ok, out = _run([
        "scripts/data_extraction.py",
        "--index", index,
        "--output", str(output_csv),
        "--hours", str(hours),
        "--host", host, "--port", str(port),
    ])
    return ok, out, str(output_csv)


def collect_logs_from_file(log_path=None, output_csv=None):
    """Collect logs from file (e.g. test.log) — offline load."""
    log_path = log_path or os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "test.log")
    output_csv = output_csv or ROOT / "data" / "raw" / "logs.csv"
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    ok, out = _run([
        "scripts/local_log_to_csv.py",
        "--input", log_path,
        "--output", str(output_csv),
    ])
    return ok, out, str(output_csv)


def load_dataset(csv_path):
    """Load dataset from CSV (offline). Returns path for downstream."""
    p = Path(csv_path)
    if not p.is_absolute():
        p = ROOT / p
    return str(p) if p.exists() else None


def write_test_log(normal=3, attack=5):
    """Write test.log (attack simulation) for ingestion."""
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    lines = []
    for i in range(1, normal + 1):
        lines.append(
            "Jan 19 10:00:%02d localhost sshd[100%d]: Accepted password for user%d from 192.168.1.%d port 22 ssh2"
            % (i, i, i, 10 + i)
        )
    for j in range(1, attack + 1):
        lines.append(
            "Jan 19 10:01:%02d localhost sshd[20%02d]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2"
            % (j, j)
        )
    text = "\n".join(lines) + "\n"
    path = Path(user) / "Documents" / "test.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return [str(path)]
    except Exception:
        return []


def get_test_log_path():
    """Return path to test.log (Documents)."""
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    return Path(user) / "Documents" / "test.log"
