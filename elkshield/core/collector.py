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
    # NOTE: Dùng timestamp gần hiện tại để Kibana/Timeline ("Last 24 hours", "5 phút gần nhất") có dữ liệu.
    # Format phải tương thích với regex parse_syslog_timestamp trong `scripts/local_log_to_csv.py`.
    from datetime import datetime, timedelta

    now = datetime.now()
    ts_normal = now - timedelta(minutes=2)
    ts_attack = now - timedelta(minutes=1)

    def _syslog_ts(ts: datetime, sec: int) -> str:
        # Example: "Mar 20 14:35:01"
        return ts.replace(second=sec, microsecond=0).strftime("%b %d %H:%M:%S")

    lines = []
    for i in range(1, normal + 1):
        sec = min(i, 59)
        lines.append(
            "{ts} localhost sshd[100{pid}]: Accepted password for user{user} from 192.168.1.{oct} port 22 ssh2".format(
                ts=_syslog_ts(ts_normal, sec),
                pid=i,
                user=i,
                oct=10 + i,
            )
        )
    for j in range(1, attack + 1):
        sec = min(j, 59)
        lines.append(
            "{ts} localhost sshd[20{pid}]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2".format(
                ts=_syslog_ts(ts_attack, sec),
                pid=str(j).zfill(2),
            )
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
