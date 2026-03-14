"""
SIEM Integration — Elasticsearch writer, index management.
Security orchestration layer.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_elasticsearch(host="127.0.0.1", port=9200, timeout=3):
    """Check if Elasticsearch is running."""
    try:
        import urllib.request
        urllib.request.urlopen("http://%s:%s" % (host, port), timeout=timeout)
        return True
    except Exception:
        return False


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


def write_alerts_to_es(
    predictions_csv,
    index_name="ml-alerts",
    host="127.0.0.1",
    port=9200,
    model_name="unified",
    timeout=300,
):
    """Write ML alerts to Elasticsearch (with defense_recommendations)."""
    predictions_csv = Path(predictions_csv)
    if not predictions_csv.is_absolute():
        predictions_csv = ROOT / predictions_csv
    ok, out = _run([
        "scripts/elasticsearch_writer.py",
        "--input", str(predictions_csv),
        "--index", index_name,
        "--host", host, "--port", str(port),
        "--model-name", model_name,
    ], timeout=timeout)
    return ok, out


def delete_indices(pattern, host="127.0.0.1", port=9200):
    """Delete Elasticsearch indices by pattern (e.g. ml-alerts-*, test-logs-*)."""
    import urllib.request
    import fnmatch
    base = "http://%s:%s" % (host, port)
    try:
        with urllib.request.urlopen("%s/_cat/indices?h=index" % base, timeout=10) as r:
            text = r.read().decode("utf-8", errors="replace").strip()
        all_names = [s.strip() for s in text.splitlines() if s.strip()]
        indices = [n for n in all_names if fnmatch.fnmatch(n, pattern)]
        for idx in indices:
            try:
                req = urllib.request.Request("%s/%s" % (base, idx), method="DELETE")
                urllib.request.urlopen(req, timeout=10)
            except Exception:
                pass
        return True, "Deleted: %s" % ", ".join(indices) if indices else "No index matched"
    except Exception as e:
        return False, str(e)
