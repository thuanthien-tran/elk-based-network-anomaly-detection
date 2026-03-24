#!/usr/bin/env python3
"""
ELKShield - ứng dụng desktop mô phỏng (SOC dashboard).
Chạy: python run_simulation_app.py
Yêu cầu: pip install PySide6
"""
import os
import sys
import subprocess
import webbrowser
import threading
import queue
import csv
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QGridLayout,
        QPushButton,
        QLabel,
        QFrame,
        QPlainTextEdit,
        QRadioButton,
        QButtonGroup,
        QCheckBox,
        QLineEdit,
        QMessageBox,
        QTableWidget,
        QTableWidgetItem,
        QAbstractItemView,
        QSizePolicy,
    )
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtGui import QColor, QFont, QPainter
    HAS_QT = True
    try:
        from PySide6.QtCharts import (
            QBarCategoryAxis,
            QBarSeries,
            QBarSet,
            QChart,
            QChartView,
            QValueAxis,
        )
        HAS_QTCHARTS = True
    except ImportError:
        HAS_QTCHARTS = False
except ImportError:
    HAS_QT = False
    HAS_QTCHARTS = False
if not HAS_QT:
    HAS_QTCHARTS = False

# --- Helpers ---
def run_cmd(args, cwd=None, timeout=600):
    cwd = cwd or str(ROOT)
    try:
        base = [sys.executable] + list(args)
        # On Windows, prefer "py -3" to avoid mixing Python envs
        if sys.platform == "win32":
            try:
                rtest = subprocess.run(
                    ["py", "-3", "-c", "import sys; print(sys.executable)"],
                    cwd=cwd,
                    timeout=5,
                    capture_output=True,
                    text=True,
                )
                if rtest.returncode == 0:
                    base = ["py", "-3"] + list(args)
            except Exception:
                pass
        r = subprocess.run(
            base,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode == 0, out.strip()
    except subprocess.TimeoutExpired:
        return False, "[Timeout] Lệnh chạy quá thời gian."
    except Exception as e:
        return False, str(e)


def run_cmd_shell(shell_cmd, cwd=None, timeout=600):
    cwd = cwd or str(ROOT)
    try:
        r = subprocess.run(
            shell_cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode == 0, out.strip()
    except Exception as e:
        return False, str(e)


def run_cmd_stream(args, cwd, timeout, queue_put):
    cwd = cwd or str(ROOT)
    cmd = [sys.executable] + list(args)
    if sys.platform == "win32":
        try:
            rtest = subprocess.run(
                ["py", "-3", "-c", "import sys; print(sys.executable)"],
                cwd=cwd,
                timeout=5,
                capture_output=True,
                text=True,
            )
            if rtest.returncode == 0:
                cmd = ["py", "-3"] + list(args)
        except Exception:
            pass
    proc = None
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
        for line in iter(proc.stdout.readline, ""):
            if line:
                queue_put(("log", line.rstrip(), False))
        proc.wait(timeout=timeout)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
        queue_put(("log", "[Timeout] Lá»‡nh cháº¡y quÃ¡ thá»i gian.", True))
        return False
    except Exception as e:
        queue_put(("log", str(e), True))
        return False


def _parse_timestamp(ts_str):
    """Parse timestamp string; try many formats and return datetime or None."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    # Keep a safe upper bound, but DO NOT truncate by `len(fmt)` because that counts
    # '%' tokens (e.g. '%Y' is 2 chars) and will cut off real timestamp digits.
    s = ts_str.strip().rstrip("Zz")[:26]
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def _is_attack_row(row, attack_keys=("is_attack", "ml_anomaly", "prediction", "is_attack_pred")):
    """Kiá»ƒm tra má»™t dÃ²ng CSV cÃ³ Ä‘Æ°á»£c coi lÃ  táº¥n cÃ´ng (true/1/yes)."""
    for key in attack_keys:
        v = str(row.get(key, "")).strip().lower()
        if v in ("true", "1", "yes"):
            return True
    return False


def _add_hourly_from_csv(csv_path, hour_counts, now, only_attacks=True, attack_keys=("is_attack", "ml_anomaly", "prediction", "is_attack_pred"), ts_keys=("timestamp", "Timestamp", "@timestamp")):
    """Äá»c CSV, Ä‘áº¿m sá»‘ báº£n ghi 'táº¥n cÃ´ng' theo giá» trong 24h qua; cá»™ng vÃ o hour_counts."""
    if not csv_path or not Path(csv_path).exists():
        return
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return
            for row in reader:
                if only_attacks and not _is_attack_row(row, attack_keys):
                    continue
                ts = None
                for k in ts_keys:
                    ts = _parse_timestamp(row.get(k, ""))
                    if ts is not None:
                        break
                if ts is None:
                    continue
                delta = now - ts
                if timedelta(0) <= delta <= timedelta(hours=24):
                    hour_key = ts.replace(minute=0, second=0, microsecond=0)
                    hour_counts[hour_key] += 1
    except Exception:
        pass


def load_stats_from_csv():
    """Äá»c thá»‘ng kÃª tá»« data/processed/logs.csv vÃ  cÃ¡c file predictions. Tráº£ vá» dict: logs_count, attacks_count, accuracy, top_ip, top_ip_count_5m, attack_today, attack_5min, hourly_attacks, ingestion_rate, alert_rate, model_version, dataset_version."""
    csv_path = ROOT / "data" / "processed" / "logs.csv"
    out = {
        "logs_count": 0,
        "attacks_count": 0,
        "accuracy": None,
        "top_ip": None,
        "top_ip_count_5m": 0,
        "attack_today": 0,
        "attack_5min": 0,
        "hourly_attacks": [0] * 24,
        "hour_labels": [],
        # Hourly summary for UI table (based on predictions files)
        "hourly_total_alerts": [0] * 24,
        "hourly_top_ip": [None] * 24,
        "hourly_top_attack_type": [None] * 24,
        "hourly_avg_score": [None] * 24,
        "hourly_top_model": [None] * 24,
        "ingestion_rate": None,   # logs/min (last hour)
        "alert_rate": None,       # alerts/hour (last hour)
        "model_version": None,
        "dataset_version": None,
    }

    # IMPORTANT:
    # "Attacks Timeline (Last 24 Hours)" should be based on the timestamps inside
    # the dataset, not on the current system time. Otherwise, when test.log uses
    # older syslog timestamps, timeline becomes empty even if detection found attacks.
    system_now = datetime.now()
    reference_now = system_now

    # Parse timestamp and normalize to Vietnam local time for UI stats/table.
    def _parse_ts_vn(raw_ts: str):
        if not raw_ts or not isinstance(raw_ts, str):
            return None
        s = raw_ts.strip()
        try:
            # Handle ISO timestamps with timezone info, e.g. "...Z", "...+00:00".
            if s.endswith("Z") or "+" in s[10:] or (len(s) > 10 and s[10] == "T" and "-" in s[11:]):
                from zoneinfo import ZoneInfo
                aware = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if aware.tzinfo is not None:
                    return aware.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)
        except Exception:
            pass
        # Fallback for naive timestamps.
        return _parse_timestamp(s)

    def _max_timestamp_in_file(p: Path):
        max_ts = None
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return None
                for row in reader:
                    ts = _parse_ts_vn(row.get("timestamp") or row.get("Timestamp") or row.get("@timestamp") or "")
                    if ts is not None and (max_ts is None or ts > max_ts):
                        max_ts = ts
        except Exception:
            return None
        return max_ts

    # Scan logs.csv first.
    # For UI timeline, we should anchor to the timestamps inside `data/processed/logs.csv`
    # (otherwise newer predictions from previous runs can push reference_now forward,
    # and old logs will be filtered out by the "last 24 hours" window).
    if csv_path.exists():
        max_ts = _max_timestamp_in_file(csv_path)
        if max_ts is not None:
            reference_now = max_ts
        else:
            reference_now = system_now
    else:
        # Fallback: use predictions if logs.csv is missing
        pred_names = ["predictions.csv", "russellmitchell_predictions.csv", "custom_predictions.csv"]
        for pred_name in pred_names:
            for base in (ROOT / "data" / "processed", ROOT / "data"):
                p = base / pred_name
                if p.exists():
                    max_ts = _max_timestamp_in_file(p)
                    if max_ts is not None:
                        reference_now = max_ts

    now = reference_now
    # Convert "hour bucket" computations to Vietnam local time (Asia/Ho_Chi_Minh).
    # Note: timestamps parsed from CSV/predictions are naive datetimes, so we assume
    # they represent the local time of the machine that generated the files.
    # Then we shift by the offset difference to align buckets with VN time.
    try:
        from zoneinfo import ZoneInfo
        local_offset = datetime.now().astimezone().utcoffset()
        vn_offset = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).utcoffset()
        tz_delta = timedelta(seconds=((vn_offset or timedelta(0)).total_seconds() - (local_offset or timedelta(0)).total_seconds()))
    except Exception:
        tz_delta = timedelta(0)
    now_vn = now + tz_delta
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_5m = now - timedelta(minutes=5)
    attack_counts_by_ip = defaultdict(int)
    attack_counts_by_ip_5m = defaultdict(int)
    hour_counts = defaultdict(int)
    hour_labels = []

    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    for row in reader:
                        out["logs_count"] += 1
                        is_attack = _is_attack_row(row, ("is_attack",))
                        if is_attack:
                            out["attacks_count"] += 1
                            src = (row.get("source_ip") or "").strip()
                            if src:
                                attack_counts_by_ip[src] += 1
                        ts = _parse_ts_vn(row.get("timestamp") or row.get("Timestamp") or row.get("@timestamp") or "")
                        if ts is not None:
                            if is_attack:
                                if ts >= today_start:
                                    out["attack_today"] += 1
                                if ts >= cutoff_5m:
                                    out["attack_5min"] += 1
                                    if src:
                                        attack_counts_by_ip_5m[src] += 1
                                delta = now - ts
                                if timedelta(0) <= delta <= timedelta(hours=24):
                                    hour_key = ts.replace(minute=0, second=0, microsecond=0)
                                    hour_counts[hour_key] += 1
            if attack_counts_by_ip:
                out["top_ip"] = max(attack_counts_by_ip, key=attack_counts_by_ip.get)
            if attack_counts_by_ip_5m:
                top = max(attack_counts_by_ip_5m, key=attack_counts_by_ip_5m.get)
                out["top_ip_count_5m"] = attack_counts_by_ip_5m[top]
        except Exception:
            pass

    # Gá»™p thÃªm tá»« file predictions (sau khi cháº¡y Detection) Ä‘á»ƒ timeline cÃ³ dá»¯ liá»‡u
    seen = set()
    for name in ["predictions.csv", "russellmitchell_predictions.csv", "custom_predictions.csv"]:
        for base in (ROOT / "data" / "processed", ROOT / "data"):
            p = base / name
            if p.exists() and str(p) not in seen:
                seen.add(str(p))
                _add_hourly_from_csv(p, hour_counts, now, only_attacks=True, attack_keys=("ml_anomaly", "prediction", "is_attack_pred", "is_attack"))
                break

    for i in range(24):
        t = (now_vn - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
        out["hourly_attacks"][i] = hour_counts.get(t, 0)
        hour_labels.append(t.strftime("%H"))
    out["hour_labels"] = hour_labels

    # Build detailed hourly stats for the attack table (predictions => alerts indexed to ES).
    # We keep the UI logic independent from model training/detection pipeline.
    hour_bucket_map = {}
    for i in range(24):
        t = (now_vn - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
        hour_bucket_map[t] = i

    hourly_total_alerts = [0] * 24
    hourly_attack_counts = [0] * 24
    hourly_top_ip_counts = [defaultdict(int) for _ in range(24)]
    hourly_top_type_counts = [defaultdict(int) for _ in range(24)]
    hourly_score_sum = [0.0] * 24
    hourly_score_cnt = [0] * 24
    # Track attack counts per model source so UI can show "Top model".
    model_priority = ["unified", "kaggle", "russellmitchell", "custom"]
    hourly_attack_counts_by_model = {k: [0] * 24 for k in model_priority}

    pred_paths = []
    for p in [
        ROOT / "data" / "predictions.csv",
        ROOT / "data" / "processed" / "predictions.csv",
        ROOT / "data" / "processed" / "russellmitchell_predictions.csv",
        ROOT / "data" / "processed" / "custom_predictions.csv",
        ROOT / "data" / "processed" / "pipeline_ssh_predictions.csv",
    ]:
        if p.exists():
            pred_paths.append(p)

    seen_pred = set()
    for p in pred_paths:
        key = str(p)
        if key in seen_pred:
            continue
        seen_pred.add(key)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                for row in reader:
                    ts = _parse_ts_vn(row.get("timestamp") or row.get("Timestamp") or row.get("@timestamp") or "")
                    if ts is None:
                        continue
                    hour_key = ts.replace(minute=0, second=0, microsecond=0)
                    if hour_key not in hour_bucket_map:
                        continue
                    hi = hour_bucket_map[hour_key]
                    hourly_total_alerts[hi] += 1
                    is_attack = _is_attack_row(row, ("is_attack",))
                    if not is_attack:
                        continue
                    hourly_attack_counts[hi] += 1
                    # Infer model source from prediction file name.
                    p_name = str(p.name).lower()
                    if p_name == "pipeline_ssh_predictions.csv":
                        model_key = "kaggle"
                    elif p_name == "russellmitchell_predictions.csv":
                        model_key = "russellmitchell"
                    elif p_name == "custom_predictions.csv":
                        model_key = "custom"
                    else:
                        # data/predictions.csv or processed/predictions.csv
                        model_key = "unified"
                    hourly_attack_counts_by_model[model_key][hi] += 1
                    src = (row.get("source_ip") or "").strip()
                    if src:
                        hourly_top_ip_counts[hi][src] += 1
                    atk_type = (row.get("attack_type") or "unknown").strip() or "unknown"
                    hourly_top_type_counts[hi][atk_type] += 1
                    score_raw = row.get("ml_anomaly_score", "")
                    try:
                        score = float(score_raw)
                        hourly_score_sum[hi] += score
                        hourly_score_cnt[hi] += 1
                    except Exception:
                        pass
        except Exception:
            pass

    out["hourly_total_alerts"] = hourly_total_alerts
    out["hourly_attacks"] = hourly_attack_counts
    out["hourly_top_ip"] = [max(d, key=d.get) if d else None for d in hourly_top_ip_counts]
    out["hourly_top_attack_type"] = [max(d, key=d.get) if d else None for d in hourly_top_type_counts]
    out["hourly_avg_score"] = [
        (hourly_score_sum[i] / hourly_score_cnt[i]) if hourly_score_cnt[i] else None for i in range(24)
    ]
    out["hourly_top_model"] = []
    model_display = {
        "unified": "Unified",
        "kaggle": "Kaggle",
        "russellmitchell": "Russell",
        "custom": "Custom",
    }
    for i in range(24):
        best_model = None
        best_count = 0
        for mk in model_priority:
            c = hourly_attack_counts_by_model.get(mk, [0] * 24)[i]
            if c > best_count:
                best_count = c
                best_model = mk
        out["hourly_top_model"].append(model_display.get(best_model) if best_model else None)

    # Log ingestion rate (logs/min, last hour) vÃ  alert rate (alerts/hour, last hour)
    cutoff_1h = now - timedelta(hours=1)
    logs_1h = attacks_1h = 0
    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts = _parse_ts_vn(row.get("timestamp") or row.get("Timestamp") or row.get("@timestamp") or "")
                    if ts and ts >= cutoff_1h:
                        logs_1h += 1
                        if _is_attack_row(row):
                            attacks_1h += 1
            if logs_1h >= 0:
                out["ingestion_rate"] = round(logs_1h / 60.0, 1) if logs_1h else 0
            out["alert_rate"] = attacks_1h
        except Exception:
            pass

    # Model version (tá»« file model hoáº·c mtime)
    model_path = ROOT / "data" / "models" / "ssh_attack_model.joblib"
    if model_path.exists():
        try:
            mtime = model_path.stat().st_mtime
            out["model_version"] = "v1.0." + datetime.fromtimestamp(mtime).strftime("%y%m%d")
        except Exception:
            out["model_version"] = "v1.0"
    # Dataset version (processed logs)
    if csv_path.exists():
        try:
            mtime = csv_path.stat().st_mtime
            out["dataset_version"] = "processed." + datetime.fromtimestamp(mtime).strftime("%y%m%d")
        except Exception:
            out["dataset_version"] = "processed"

    try:
        for name in ["russellmitchell_predictions.csv", "custom_predictions.csv", "predictions.csv"]:
            p = ROOT / "data" / "processed" / name
            if not p.exists():
                p = ROOT / "data" / name
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as pf:
                        pr = csv.DictReader(pf)
                        correct = total = 0
                        for r in pr:
                            total += 1
                            a = str(r.get("is_attack", "")).strip().lower() == "true"
                            pred = (r.get("prediction") or r.get("is_attack_pred", "")).strip().lower()
                            if pred in ("true", "1", "yes"):
                                if a:
                                    correct += 1
                            else:
                                if not a:
                                    correct += 1
                        if total > 0:
                            out["accuracy"] = round(100.0 * correct / total, 1)
                            break
                except Exception:
                    pass
    except Exception:
        pass
    return out


def check_elasticsearch():
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:9200", timeout=3)
        return True
    except Exception:
        return False


def check_kibana():
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:5601", timeout=3)
        return True
    except Exception:
        return False


def check_source_log_indices(
    host="127.0.0.1",
    port=9200,
    patterns=None,
    timeout=5,
):
    """
    Check whether source log indices exist in Elasticsearch.
    Returns (ok: bool, msg: str, matched: list[str]).
    """
    import urllib.request
    import fnmatch

    if patterns is None:
        patterns = ["test-logs-*", "ssh-logs-*", "filebeat-*", "logstash-*", "logs-*"]
    try:
        url = f"http://{host}:{port}/_cat/indices?h=index,docs.count"
        with urllib.request.urlopen(url, timeout=timeout) as r:
            text = r.read().decode("utf-8", errors="replace").strip()
        matched = []
        for line in text.splitlines():
            parts = [p for p in line.split() if p]
            if len(parts) < 2:
                continue
            idx, docs = parts[0], parts[1]
            if idx.startswith(".") or idx.startswith("ml-alerts-"):
                continue
            if any(fnmatch.fnmatch(idx, p) for p in patterns):
                try:
                    if int(docs) > 0:
                        matched.append(idx)
                except Exception:
                    matched.append(idx)
        if matched:
            return True, f"Đã tìm thấy index log nguồn: {', '.join(sorted(set(matched))[:8])}", sorted(set(matched))
        return False, "Không thấy index log nguồn có dữ liệu (test-logs/ssh-logs/filebeat/logstash/logs).", []
    except Exception as e:
        return False, f"Không kiểm tra được index log nguồn trên ES: {e}", []


def fetch_latest_alerts_from_es(
    index_pattern="ml-alerts-*",
    limit=10,
    host="127.0.0.1",
    port=9200,
    timeout=6,
    since_ts=None,
    model_name=None,
):
    """
    Fetch latest alert documents from Elasticsearch for in-app reporting.
    Returns: (ok: bool, message: str, alerts: list[dict])
    """
    import urllib.request

    base = f"http://{host}:{port}"
    url = f"{base}/{index_pattern}/_search"
    query = {
        "size": int(limit),
        "sort": [{"@timestamp": {"order": "desc"}}],
        "_source": [
            "@timestamp",
            "source_ip",
            "is_attack",
            "attack_type",
            "ml_model",
            "ml_anomaly",
            "ml_anomaly_score",
            "defense_recommendations",
        ],
    }
    must_filters = []
    if since_ts:
        must_filters.append({"range": {"@timestamp": {"gte": since_ts}}})
    if model_name:
        must_filters.append({"term": {"ml_model.keyword": str(model_name)}})
    if must_filters:
        query["query"] = {"bool": {"must": must_filters}}
    data = json.dumps(query).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
        hits = (((payload.get("hits") or {}).get("hits")) or [])
        alerts = []
        for h in hits:
            src = h.get("_source") or {}
            alerts.append(src)
        msg = f"Đã lấy {len(alerts)} cảnh báo mới nhất từ {index_pattern}."
        return True, msg, alerts
    except Exception as e:
        return False, f"Không lấy được cảnh báo từ Elasticsearch: {e}", []


def fetch_latest_alerts_from_predictions_csv(
    limit=10,
    model_name=None,
):
    """
    Fallback giống run detection:
    Nếu ES không lấy được (ES tắt / index chưa sẵn), đọc trực tiếp data/predictions.csv (hoặc các file predictions tương tự)
    để tạo danh sách alert cùng format với fetch_latest_alerts_from_es.
    """
    pred_paths = [
        ROOT / "data" / "predictions.csv",
        ROOT / "data" / "processed" / "predictions.csv",
        ROOT / "data" / "processed" / "pipeline_ssh_predictions.csv",
        ROOT / "data" / "processed" / "russellmitchell_predictions.csv",
        ROOT / "data" / "processed" / "custom_predictions.csv",
    ]
    csv_path = None
    for p in pred_paths:
        if p.exists():
            csv_path = p
            break

    if not csv_path:
        return False, "Chưa có predictions.csv để fallback (chạy Detection trước).", []

    try:
        docs = []
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return False, f"File predictions rỗng: {csv_path}", []

            for row in reader:
                # Predictions có cột timestamp kiểu: "YYYY-MM-DD HH:MM:SS"
                ts = _parse_timestamp(row.get("timestamp") or row.get("Timestamp") or row.get("@timestamp") or "")
                if ts is None:
                    continue
                # Tạo @timestamp dạng ISO+Z để UI display đồng nhất
                at = ts.replace(microsecond=0).isoformat() + "Z"
                docs.append(
                    {
                        "@timestamp": at,
                        "source_ip": row.get("source_ip") or "—",
                        "is_attack": row.get("is_attack", False),
                        "attack_type": row.get("attack_type") or "unknown",
                        "ml_model": model_name or row.get("ml_model") or "—",
                        "ml_anomaly": row.get("ml_anomaly", False),
                        "ml_anomaly_score": row.get("ml_anomaly_score"),
                        "defense_recommendations": row.get("defense_recommendations") or "—",
                    }
                )

        docs.sort(key=lambda d: d.get("@timestamp") or "", reverse=True)
        docs = docs[: int(limit)]
        msg = f"Fallback: lấy {len(docs)} cảnh báo từ {csv_path.name}."
        return True, msg, docs
    except Exception as e:
        return False, f"Fallback đọc predictions thất bại: {e}", []


def summarize_predictions_csv(model_name=None):
    """
    Read full predictions CSV (fallback) and return quick summary:
    (ok, msg, total, ml_attacks, rule_attacks, top_ip)
    """
    pred_paths = [
        ROOT / "data" / "predictions.csv",
        ROOT / "data" / "processed" / "predictions.csv",
        ROOT / "data" / "processed" / "pipeline_ssh_predictions.csv",
        ROOT / "data" / "processed" / "russellmitchell_predictions.csv",
        ROOT / "data" / "processed" / "custom_predictions.csv",
    ]
    csv_path = None
    for p in pred_paths:
        if p.exists():
            csv_path = p
            break
    if not csv_path:
        return False, "No predictions file.", 0, 0, 0, None
    total = ml_attacks = rule_attacks = 0
    ip_counts = defaultdict(int)
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return False, f"Empty predictions file: {csv_path}", 0, 0, 0, None
            for row in reader:
                total += 1
                if _to_bool(row.get("ml_anomaly", False)):
                    ml_attacks += 1
                if _to_bool(row.get("is_attack", False)):
                    rule_attacks += 1
                ip = (row.get("source_ip") or "").strip()
                if ip:
                    ip_counts[ip] += 1
        top_ip = max(ip_counts, key=ip_counts.get) if ip_counts else None
        return True, f"Summary from {csv_path.name}", total, ml_attacks, rule_attacks, top_ip
    except Exception as e:
        return False, str(e), 0, 0, 0, None


def write_incident_report(
    report_source,
    model_name,
    run_index_pattern,
    decision,
    total_records,
    ml_count,
    rule_count,
    top_alerts,
    defense_checklist,
):
    """
    Write incident report to ./report with datetime-based filename.
    Returns: (ok, path_or_error)
    """
    try:
        total_records_i = int(total_records or 0)
        ml_count_i = int(ml_count or 0)
        rule_count_i = int(rule_count or 0)

        def _clean_text(v):
            s = str(v or "").strip()
            if s in ("", "—", "-", "N/A", "n/a", "None", "null"):
                return ""
            return s

        def _to_float_or_none(v):
            try:
                if v is None:
                    return None
                s = str(v).strip()
                if s in ("", "—", "-", "N/A", "n/a", "None", "null"):
                    return None
                return float(s)
            except Exception:
                return None

        is_fallback = "fallback" in str(report_source or "").lower()
        run_index_value = _clean_text(run_index_pattern)
        if is_fallback:
            run_index_value = run_index_value or "N/A (fallback mode)"

        if ml_count_i > 0:
            severity = "high" if ml_count_i >= max(3, total_records_i // 5) else "medium"
        elif rule_count_i > 0:
            severity = "low"
        else:
            severity = "info"

        if ml_count_i > 0:
            executive_conclusion = f"ML detected {ml_count_i} anomalous events; investigate immediately."
        elif rule_count_i > 0:
            executive_conclusion = "No ML anomaly detected; rule-based suspicious activity observed."
        else:
            executive_conclusion = "No suspicious activity detected in current report scope."

        data_scope = "preview_10_records" if total_records_i <= 10 else "expanded_records"
        if is_fallback:
            data_scope += "_from_predictions_csv"

        normalized_alerts = []
        for a in (top_alerts or []):
            normalized_alerts.append(
                {
                    "timestamp": _clean_text(a.get("timestamp")) or "unknown",
                    "source_ip": _clean_text(a.get("source_ip")) or "unknown",
                    "attack_type": _clean_text(a.get("attack_type")) or "unknown",
                    "ml_model": _clean_text(a.get("ml_model")) or _clean_text(model_name) or "unknown",
                    "ml_anomaly_score": _to_float_or_none(a.get("ml_anomaly_score")),
                    "ml_label": _clean_text(a.get("ml_label")) or "unknown",
                    "rule_label": _clean_text(a.get("rule_label")) or "unknown",
                    "defense_recommendations": _clean_text(a.get("defense_recommendations")) or "No recommendation in this record.",
                }
            )

        normalized_checklist = [
            x for x in [str(item or "").strip() for item in (defense_checklist or [])]
            if x and x not in ("—", "-", "N/A", "n/a", "None", "null")
        ]
        if not normalized_checklist:
            normalized_checklist = [
                "Review source logs and validate parsing pipeline.",
                "Correlate suspicious IPs with firewall/SSH auth logs.",
                "Run detection again with a larger data window before final conclusion.",
            ]

        next_actions = []
        if ml_count_i > 0:
            next_actions.extend([
                "Open Alert Feed and inspect Top-3 alerts by anomaly score.",
                "Apply temporary mitigation for top suspicious IPs.",
                "Export evidence (logs + predictions + this report) for review.",
            ])
        elif rule_count_i > 0:
            next_actions.extend([
                "Treat as early warning and monitor the same IPs closely.",
                "Verify whether rules are too sensitive for this traffic profile.",
                "Re-run detection after collecting more recent logs.",
            ])
        else:
            next_actions.extend([
                "Keep monitoring and collect more data for the next run.",
                "Validate Filebeat/Logstash ingestion continuity.",
            ])

        report_dir = ROOT / "report"
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"incident_{ts}.json"
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": _clean_text(report_source) or "unknown",
            "model": _clean_text(model_name) or "unknown",
            "run_index": run_index_value or "unknown",
            "decision": decision,
            "executive_conclusion": executive_conclusion,
            "severity": severity,
            "data_scope": data_scope,
            "summary": {
                "records": total_records_i,
                "ml_anomalies": ml_count_i,
                "rule_warnings": rule_count_i,
            },
            "top_alerts": normalized_alerts,
            "defense_checklist": normalized_checklist,
            "next_actions": next_actions,
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True, str(report_path)
    except Exception as e:
        return False, str(e)


def _to_bool(v) -> bool:
    """Convert ES/CSV values to boolean safely for in-app reporting."""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        return s in ("true", "1", "yes", "y", "t")
    return False


def _glob_indices(pattern: str, names: list) -> list:
    """Lá»c danh sÃ¡ch tÃªn index theo pattern (vd: ml-alerts-* -> báº¯t Ä‘áº§u báº±ng ml-alerts-)."""
    import fnmatch
    return [n for n in names if fnmatch.fnmatch(n, pattern)]


def delete_elasticsearch_indices(pattern: str, host: str = "127.0.0.1", port: int = 9200):
    """Liệt kê index theo pattern rồi xóa toàn bộ (ES có thể không xóa được khi DELETE trực tiếp wildcard)."""
    import urllib.request
    base = f"http://{host}:{port}"
    deleted = []
    errors = []
    try:
        # Thá»­ _cat/indices/<pattern>; náº¿u 404 hoáº·c rá»—ng thÃ¬ láº¥y toÃ n bá»™ rá»“i lá»c
        list_url = f"{base}/_cat/indices/{pattern}?h=index"
        indices = []
        try:
            req = urllib.request.Request(list_url)
            with urllib.request.urlopen(req, timeout=10) as r:
                text = r.read().decode("utf-8", errors="replace").strip()
            indices = [s.strip() for s in text.splitlines() if s.strip()]
        except Exception:
            pass
        if not indices:
            with urllib.request.urlopen(f"{base}/_cat/indices?h=index", timeout=10) as r:
                text = r.read().decode("utf-8", errors="replace").strip()
            all_names = [s.strip() for s in text.splitlines() if s.strip()]
            indices = _glob_indices(pattern, all_names)
        if not indices:
            return True, f"Không có index nào khớp {pattern}"
        for idx in indices:
            try:
                del_req = urllib.request.Request(f"{base}/{idx}", method="DELETE")
                with urllib.request.urlopen(del_req, timeout=10) as dr:
                    dr.read()
                deleted.append(idx)
            except Exception as e:
                errors.append(f"{idx}: {e}")
        if errors:
            return False, "; ".join(errors)
        return True, f"Đã xóa: {', '.join(deleted)}"
    except Exception as e:
        return False, str(e)


def get_testlog_path():
    """ÄÆ°á»ng dáº«n file test.log trong thÆ° má»¥c Documents (cÃ¹ng chá»— Ghi test.log ghi vÃ o)."""
    import tempfile
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME") or tempfile.gettempdir()
    return Path(user) / "Documents" / "test.log"


def write_sample_log(normal: int, attack: int):
    import tempfile
    from datetime import datetime, timedelta
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME") or tempfile.gettempdir()
    lines = []

    # Use recent timestamps with valid second range for robust parsing/ingestion.
    now = datetime.now().replace(microsecond=0)
    normal_start = now - timedelta(minutes=2)
    attack_start = now - timedelta(minutes=1)

    def _syslog_ts(start_dt: datetime, offset_sec: int) -> str:
        # offset_sec may exceed 59; timedelta handles rollover safely.
        return (start_dt + timedelta(seconds=offset_sec)).strftime("%b %d %H:%M:%S")

    for i in range(1, normal + 1):
        ts = _syslog_ts(normal_start, i - 1)
        pid = 1000 + i
        ip_octet = 10 + ((i - 1) % 200)
        lines.append(
            f"{ts} localhost sshd[{pid}]: Accepted password for user{i} from 192.168.1.{ip_octet} port 22 ssh2"
        )
    for j in range(1, attack + 1):
        ts = _syslog_ts(attack_start, j - 1)
        pid = 2000 + j
        lines.append(
            f"{ts} localhost sshd[{pid}]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2"
        )
    text = "\n".join(lines) + "\n"
    paths = [
        Path(user) / "Desktop" / "test.log",
        Path(user) / "Documents" / "test.log",
    ]
    written = []
    for p in paths:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            written.append(str(p))
        except Exception:
            pass
    return written


# --- PySide6 SOC Dashboard ---
if HAS_QT:
    _BG_DARK = "#0d1117"
    _BG_CARD = "#161b22"
    _BORDER = "#21262d"
    _TEXT = "#c9d1d9"
    _TEXT_MUTED = "#8b949e"
    _ACCENT_BLUE = "#58a6ff"
    _ACCENT_GREEN = "#3fb950"
    _STATUS_OK = "#3fb950"
    _STATUS_FAIL = "#f85149"
    _COLOR_SETUP = "#58a6ff"
    _COLOR_TRAINING = "#a371f7"
    _COLOR_DETECTION = "#3fb950"
    _COLOR_MONITORING = "#f0883e"

    _QT_STYLE = f"""
    QMainWindow, QWidget {{ background-color: {_BG_DARK}; }}
    QLabel {{ color: {_TEXT}; }}
    QFrame#card {{ background-color: {_BG_CARD}; border: 1px solid {_BORDER}; border-radius: 12px; }}
    QFrame#statusPill {{ background-color: {_BG_CARD}; border: 1px solid {_BORDER}; border-radius: 20px; }}
    QPushButton#runBtn {{ background-color: {_ACCENT_GREEN}; color: white; border: none; border-radius: 10px; }}
    QPushButton#runBtn:hover {{ background-color: #2ea043; }}
    QPushButton#runBtn:disabled {{ background-color: #238636; color: #8b949e; }}
    QPlainTextEdit {{ background-color: {_BG_DARK}; color: {_TEXT}; border: 1px solid {_BORDER}; border-radius: 8px;
        font-family: Consolas, Monaco, 'Courier New', monospace; font-size: 11px; padding: 8px; }}
    QRadioButton, QCheckBox {{ color: {_TEXT}; }}
    QLineEdit {{ background-color: {_BG_CARD}; color: {_TEXT}; border: 1px solid {_BORDER}; border-radius: 6px; padding: 6px; }}
    """

    class SimulationAppQt(QMainWindow):
        log_signal = Signal(str, bool)
        refresh_done_signal = Signal(object)

        def _lighten(self, hex_color, amount=35):
            h = hex_color.lstrip("#")
            if len(h) != 6:
                return hex_color
            r = min(255, int(h[0:2], 16) + amount)
            g = min(255, int(h[2:4], 16) + amount)
            b = min(255, int(h[4:6], 16) + amount)
            return f"#{r:02x}{g:02x}{b:02x}"

        def __init__(self):
            super().__init__()
            (ROOT / "data" / "raw").mkdir(parents=True, exist_ok=True)
            (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
            (ROOT / "data" / "models").mkdir(parents=True, exist_ok=True)
            (ROOT / "data" / "training").mkdir(parents=True, exist_ok=True)
            self.setWindowTitle("ELKShield – Mô phỏng")
            self.setMinimumSize(960, 620)
            self.resize(1180, 720)
            self.setStyleSheet(_QT_STYLE)
            self.confirm_reset = False
            self.running = False
            self.msg_queue = queue.Queue()
            self.selected_action = None
            self.action_buttons = []

            # Layout constants (gá»n)
            _MARGIN = 10
            _CARD_PAD = 10
            _CARD_GAP = 8
            _BTN_GAP = 4
            _BTN_HEIGHT = 34
            _CARD_RADIUS = 8
            _BTN_RADIUS = 6

            central = QWidget()
            self.setCentralWidget(central)
            main_layout = QVBoxLayout(central)
            main_layout.setSpacing(_CARD_GAP)
            main_layout.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)

            # 1) Header: ELKShield + subtitle
            title = QLabel("ELKShield")
            title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {_TEXT};")
            main_layout.addWidget(title)
            sub = QLabel("Intelligent Network Security Monitoring")
            sub.setStyleSheet(f"font-size: 10px; color: {_TEXT_MUTED};")
            main_layout.addWidget(sub)

            # 2) Status: Elasticsearch, Filebeat, Model (với chấm màu)
            status_pill = QFrame()
            status_pill.setObjectName("statusPill")
            status_layout = QHBoxLayout(status_pill)
            status_layout.setContentsMargins(_CARD_PAD, 5, _CARD_PAD, 5)
            status_layout.setSpacing(12)
            self.lbl_es = QLabel("Elasticsearch: —")
            self.lbl_fb = QLabel("Filebeat: —")
            self.lbl_model = QLabel("Mô hình: —")
            for lbl in (self.lbl_es, self.lbl_fb, self.lbl_model):
                lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
                status_layout.addWidget(lbl)
            status_layout.addStretch()
            self.lbl_last_refresh = QLabel("Last refresh: —")
            self.lbl_last_refresh.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
            status_layout.addWidget(self.lbl_last_refresh)
            main_layout.addWidget(status_pill)
            QTimer.singleShot(500, self._update_status_bar_qt)

            # 3) Dòng filter/stats: Log đã xử lý, Tấn công, Độ chính xác, IP / Tấn công (5 phút)
            stats_row = QHBoxLayout()
            stats_row.setSpacing(12)
            self.lbl_logs = QLabel("Logs: —")
            self.lbl_attacks = QLabel("Attacks: —")
            self.lbl_accuracy = QLabel("Score: —")
            self.lbl_topip = QLabel("Top IP: —  |  Attack 5m: —")
            for l in (self.lbl_logs, self.lbl_attacks, self.lbl_accuracy, self.lbl_topip):
                l.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
                stats_row.addWidget(l)
            stats_row.addStretch()
            main_layout.addLayout(stats_row)
            # 3b) Platform metrics: Log ingestion rate, Alert rate, Model version, Dataset version
            stats_row2 = QHBoxLayout()
            stats_row2.setSpacing(12)
            self.lbl_ingestion_rate = QLabel("Ingest: —")
            self.lbl_alert_rate = QLabel("Alert: —")
            self.lbl_model_ver = QLabel("Model version: —")
            self.lbl_dataset_ver = QLabel("Dataset version: —")
            for l in (self.lbl_ingestion_rate, self.lbl_alert_rate, self.lbl_model_ver, self.lbl_dataset_ver):
                l.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
                stats_row2.addWidget(l)
            stats_row2.addStretch()
            main_layout.addLayout(stats_row2)

            _CARD_STYLE = f"QFrame#card {{ background-color: {_BG_CARD}; border: 1px solid {_BORDER}; border-radius: {_CARD_RADIUS}px; }}"

            # 4) Phần trên: 2 cột — Logs Processed | Terminal Output
            top_row = QHBoxLayout()
            top_row.setSpacing(_CARD_GAP)

            # TrÃ¡i: Logs Processed (thá»‘ng kÃª Ä‘áº§y Ä‘á»§ + status)
            logs_card = QFrame()
            logs_card.setObjectName("card")
            logs_card.setStyleSheet(_CARD_STYLE)
            logs_card.setMinimumWidth(300)
            logs_inner = QVBoxLayout(logs_card)
            logs_inner.setContentsMargins(_CARD_PAD, _CARD_PAD, _CARD_PAD, _CARD_PAD)
            logs_inner.setSpacing(6)
            logs_head = QHBoxLayout()
            logs_title = QLabel("📄 System Snapshot")
            logs_title.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {_TEXT};")
            logs_head.addWidget(logs_title)
            logs_head.addStretch()
            self.btn_refresh = QPushButton("Làm mới")
            self.btn_refresh.setFixedHeight(28)
            self.btn_refresh.setStyleSheet(
                f"QPushButton {{ background-color: {_BORDER}; color: {_TEXT}; border: 1px solid {_TEXT_MUTED}; "
                f"border-radius: 6px; font-size: 10px; }} QPushButton:hover {{ background-color: {_TEXT_MUTED}; color: {_BG_DARK}; }}"
            )
            self.btn_refresh.clicked.connect(self._restart_app_qt)
            logs_head.addWidget(self.btn_refresh)
            logs_inner.addLayout(logs_head)
            # Các dòng: Nhãn + giá trị
            def stat_row(label, value_widget, value_color=_ACCENT_BLUE):
                r = QHBoxLayout()
                r.addWidget(QLabel(label))
                value_widget.setStyleSheet(f"color: {value_color}; font-size: 12px; font-weight: bold;")
                r.addWidget(value_widget)
                r.addStretch()
                return r
            self.metric_logs = QLabel("—")
            self.metric_attacks = QLabel("—")
            self.metric_accuracy = QLabel("—")
            self.metric_topip = QLabel("—")
            self.metric_attack_today = QLabel("—")
            self.metric_attack_5m = QLabel("—")
            logs_inner.addLayout(stat_row("Logs:", self.metric_logs))
            logs_inner.addLayout(stat_row("Attacks:", self.metric_attacks, _ACCENT_GREEN))
            logs_inner.addLayout(stat_row("Model score:", self.metric_accuracy, "#e6a23c"))
            logs_inner.addLayout(stat_row("Top IP:", self.metric_topip, "#f56c6c"))
            logs_inner.addLayout(stat_row("Attack (24h):", self.metric_attack_today))
            logs_inner.addLayout(stat_row("Attack (5 min):", self.metric_attack_5m))
            sub_status = QHBoxLayout()
            sub_status.setSpacing(8)
            self.metric_es_badge = QLabel("ES: —")
            self.metric_fb_badge = QLabel("Filebeat: —")
            self.metric_model_badge = QLabel("Model: —")
            for b in (self.metric_es_badge, self.metric_fb_badge, self.metric_model_badge):
                b.setStyleSheet(
                    f"color: {_TEXT}; background: {_BORDER}; border: 1px solid {_TEXT_MUTED}; "
                    "border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 600;"
                )
                sub_status.addWidget(b)
            sub_status.addStretch()
            logs_inner.addLayout(sub_status)
            top_row.addWidget(logs_card, 1)

            # Phải: Terminal Output (workflow text + timeline placeholder + log)
            term_card = QFrame()
            term_card.setObjectName("card")
            term_card.setStyleSheet(_CARD_STYLE)
            term_inner = QVBoxLayout(term_card)
            term_inner.setContentsMargins(_CARD_PAD, _CARD_PAD, _CARD_PAD, _CARD_PAD)
            term_inner.setSpacing(8)
            term_title = QLabel("Terminal Output")
            term_title.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {_TEXT};")
            term_inner.addWidget(term_title)
            workflow_lbl = QLabel(
                "ELKShield Unified Security Platform — Bấm ▶ Start Security Workflow (hoặc chọn thao tác rồi bấm). "
                "Luồng: Check ELK → Load Model → Collect Logs → Feature Extraction → ML Detection → Write Alert ES → Suggest Defense → Dashboard."
            )
            workflow_lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
            workflow_lbl.setWordWrap(True)
            term_inner.addWidget(workflow_lbl)
            timeline_lbl = QLabel("Attack Hourly Table (Last 24h)")
            timeline_lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
            # Header: table title + clear button
            timeline_head = QHBoxLayout()
            timeline_head.setContentsMargins(0, 0, 0, 0)
            timeline_head.setSpacing(8)
            timeline_head.addWidget(timeline_lbl)
            timeline_head.addStretch()
            self.btn_clear_attack_table = QPushButton("Xóa bảng")
            self.btn_clear_attack_table.setFixedHeight(22)
            self.btn_clear_attack_table.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {_TEXT_MUTED}; border: 1px solid {_BORDER}; "
                f"border-radius: 6px; font-size: 10px; padding: 1px 6px; }} "
                f"QPushButton:hover {{ color: {_TEXT}; border-color: {_TEXT_MUTED}; background-color: {_BG_CARD}; }}"
            )
            self.btn_clear_attack_table.clicked.connect(self._clear_attack_table_qt)
            timeline_head.addWidget(self.btn_clear_attack_table)
            term_inner.addLayout(timeline_head)
            self.chart_container = QWidget()
            chart_layout = QVBoxLayout(self.chart_container)
            chart_layout.setContentsMargins(0, 0, 0, 0)
            self.chart_placeholder = QLabel("Đang tải…")
            self.chart_placeholder.setMinimumHeight(120)
            self.chart_placeholder.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px; background: {_BG_DARK}; border-radius: 6px;")
            self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(self.chart_placeholder)
            self.chart_view = None
            # Preserve current Attack Hourly Table once (used after Reset dữ liệu).
            self._preserve_attack_table_once = False
            term_inner.addWidget(self.chart_container)
            self.txt = QPlainTextEdit()
            self.txt.setReadOnly(True)
            self.txt.setPlainText(
                "Chọn thao tác (bấm nút ở 4 cột bên dưới) rồi bấm ▶ Start Security Workflow. Kết quả hiển thị ở đây."
            )
            term_inner.addWidget(self.txt)
            top_row.addWidget(term_card, 2)

            main_layout.addLayout(top_row)

            # 5) Phần dưới: 4 cột — System Setup | Dataset & Training | Detection Pipeline | Monitoring
            def add_card(icon, title_text, color, buttons_list):
                card = QFrame()
                card.setObjectName("card")
                card.setStyleSheet(_CARD_STYLE)
                card.setMinimumWidth(180)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(_CARD_PAD, _CARD_PAD, _CARD_PAD, _CARD_PAD)
                card_layout.setSpacing(6)
                tit = QLabel(f"{icon}  {title_text}")
                tit.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {color};")
                card_layout.addWidget(tit)
                items = list(buttons_list)
                light = self._lighten(color)
                btn_style = (
                    f"QPushButton {{ background-color: {color}; color: white; border: 2px solid transparent; "
                    f"padding: 4px 8px; font-size: 10px; min-height: {_BTN_HEIGHT}px; border-radius: {_BTN_RADIUS}px; }} "
                    f"QPushButton:hover {{ background-color: {light}; }} "
                    f"QPushButton:checked {{ background-color: {light}; border: 3px solid white; }}"
                )
                ncols = 2 if len(items) in (2, 3, 4) else min(len(items), 3)
                grid = QGridLayout()
                grid.setHorizontalSpacing(_BTN_GAP)
                grid.setVerticalSpacing(_BTN_GAP)
                for i, (label, action_str) in enumerate(items):
                    btn = QPushButton(label)
                    btn.setFixedHeight(_BTN_HEIGHT)
                    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    btn.setStyleSheet(btn_style)
                    btn.setCheckable(True)
                    btn.clicked.connect(lambda checked, s=action_str: self._select_action_qt(s))
                    row, col = i // ncols, i % ncols
                    grid.addWidget(btn, row, col)
                    self.action_buttons.append((action_str, btn, color))
                for c in range(ncols):
                    grid.setColumnStretch(c, 1)
                card_layout.addLayout(grid)
                return card

            four_cols = QHBoxLayout()
            four_cols.setSpacing(_CARD_GAP)
            four_cols.addWidget(add_card("", "System Control", _COLOR_SETUP, [
                ("Start SIEM", "Start SIEM"),
                ("Reset Data", "1. Reset dữ liệu (xóa index)"),
                ("Start/Restart Filebeat", "2. Má»Ÿ Filebeat (cá»­a sá»• má»›i)"),
            ]))
            four_cols.addWidget(add_card("", "Model Lab", _COLOR_TRAINING, [
                ("Train Global Model", "6.1 Train UNIFIED (gá»™p dataset)"),
                ("Custom CSV", "6.2 Train Custom CSV"),
            ]))
            four_cols.addWidget(add_card("", "Detection Pipeline", _COLOR_DETECTION, [
                ("Run Detection", "7. Detection online (→ ml-alerts)"),
            ]))
            four_cols.addWidget(add_card("", "Threat Intelligence", _COLOR_MONITORING, [
                ("Index Management", "12. Stack Management"),
            ]))
            main_layout.addLayout(four_cols)

            # 6) Thanh dÆ°á»›i: Execute button (trÃ¡i) + Log máº«u (pháº£i)
            bottom_bar = QHBoxLayout()
            bottom_bar.setSpacing(12)
            self.btn_run = QPushButton("  ▶  Start Security Workflow  ")
            self.btn_run.setObjectName("runBtn")
            self.btn_run.setFixedHeight(_BTN_HEIGHT)
            self.btn_run.setMinimumWidth(220)
            self.btn_run.clicked.connect(self._on_run_qt)
            bottom_bar.addWidget(self.btn_run)

            self.frame_training_src = QWidget()
            training_src_layout = QVBoxLayout(self.frame_training_src)
            training_src_layout.setContentsMargins(0, 0, 0, 0)
            row1 = QHBoxLayout()
            row1.addWidget(QLabel("Nguồn:"))
            self.training_src_group = QButtonGroup()
            for lab, val in [
                ("Custom (tệp CSV)", "custom"),
            ]:
                rb = QRadioButton(lab)
                rb.setProperty("value", val)
                if val == "custom":
                    rb.setChecked(True)
                rb.toggled.connect(self._on_scenario_src_toggled)
                self.training_src_group.addButton(rb)
                row1.addWidget(rb)
            row1.addStretch()
            training_src_layout.addLayout(row1)
            self.frame_scenario_custom = QWidget()
            custom_row_layout = QHBoxLayout(self.frame_scenario_custom)
            custom_row_layout.setContentsMargins(0, 4, 0, 0)
            custom_row_layout.addWidget(QLabel("Tệp Custom:"))
            self.entry_scenario_custom = QLineEdit()
            self.entry_scenario_custom.setPlaceholderText("data/raw/my.csv hoặc đường dẫn CSV")
            self.entry_scenario_custom.setMinimumWidth(200)
            custom_row_layout.addWidget(self.entry_scenario_custom)
            self.write_es_scenario_cb = QCheckBox("Ghi ES sau train")
            self.write_es_scenario_cb.setChecked(True)
            custom_row_layout.addWidget(self.write_es_scenario_cb)
            custom_row_layout.addStretch()
            training_src_layout.addWidget(self.frame_scenario_custom)
            self.frame_scenario_custom.hide()
            bottom_bar.addWidget(self.frame_training_src)
            self.frame_training_src.hide()

            self.frame_csv = QWidget()
            csv_layout = QHBoxLayout(self.frame_csv)
            csv_layout.setContentsMargins(0, 0, 0, 0)
            csv_layout.addWidget(QLabel("CSV:"))
            self.csv_group = QButtonGroup()
            for lab, val in [("Kaggle (ssh_anomaly_dataset)", "B"), ("Tệp (đường dẫn)", "C")]:
                rb = QRadioButton(lab)
                rb.setProperty("value", val)
                if val == "B":
                    rb.setChecked(True)
                self.csv_group.addButton(rb)
                csv_layout.addWidget(rb)
            self.entry_csv = QLineEdit()
            self.entry_csv.setPlaceholderText("data/raw/my.csv")
            self.entry_csv.setMaximumWidth(180)
            csv_layout.addWidget(self.entry_csv)
            self.write_es_cb = QCheckBox("Ghi ES")
            self.write_es_cb.setChecked(True)
            csv_layout.addWidget(self.write_es_cb)
            bottom_bar.addWidget(self.frame_csv)
            self.frame_csv.hide()

            self.frame_reset_opts = QWidget()
            reset_layout = QHBoxLayout(self.frame_reset_opts)
            self.reset_del_model_cb = QCheckBox("Xóa cả model khi Reset")
            reset_layout.addWidget(self.reset_del_model_cb)
            self.reset_del_processed_cb = QCheckBox("Xóa cả dữ liệu đã xử lý (logs.csv, predictions)")
            reset_layout.addWidget(self.reset_del_processed_cb)
            bottom_bar.addWidget(self.frame_reset_opts)
            self.frame_reset_opts.hide()

            # Máº·c Ä‘á»‹nh chá»n Start SIEM Ä‘á»ƒ demo chá»‰ cáº§n báº¥m "Start Security Workflow"
            self._select_action_qt("Start SIEM")

            bottom_bar.addStretch()
            log_row = QHBoxLayout()
            log_row.setSpacing(6)
            self.btn_toggle_log = QPushButton("Ghi log")
            self.btn_toggle_log.setFixedHeight(_BTN_HEIGHT)
            self.btn_toggle_log.setFixedWidth(70)
            self.btn_toggle_log.setStyleSheet(
                f"QPushButton {{ background-color: {_BORDER}; color: {_TEXT}; border: 1px solid {_TEXT_MUTED}; "
                f"border-radius: {_BTN_RADIUS}px; }} QPushButton:hover {{ background-color: {_TEXT_MUTED}; color: {_BG_DARK}; }}"
            )
            self.btn_toggle_log.clicked.connect(self._toggle_log_panel_qt)
            log_row.addWidget(self.btn_toggle_log)

            # Panel nháº­p sá»‘ dÃ²ng (áº©n máº·c Ä‘á»‹nh)
            self.frame_log_panel = QWidget()
            panel = QHBoxLayout(self.frame_log_panel)
            panel.setContentsMargins(0, 0, 0, 0)
            panel.setSpacing(6)
            panel.addWidget(QLabel("Normal:"))
            self.spin_normal = QLineEdit()
            self.spin_normal.setFixedWidth(40)
            self.spin_normal.setText("2")
            panel.addWidget(self.spin_normal)
            panel.addWidget(QLabel("Attack:"))
            self.spin_attack = QLineEdit()
            self.spin_attack.setFixedWidth(40)
            self.spin_attack.setText("5")
            panel.addWidget(self.spin_attack)
            self.btn_do_write = QPushButton("Ghi log")
            self.btn_do_write.setFixedHeight(_BTN_HEIGHT)
            self.btn_do_write.setFixedWidth(70)
            self.btn_do_write.setStyleSheet(
                f"QPushButton {{ background-color: {_BORDER}; color: {_TEXT}; border: 1px solid {_TEXT_MUTED}; "
                f"border-radius: {_BTN_RADIUS}px; }} QPushButton:hover {{ background-color: {_TEXT_MUTED}; color: {_BG_DARK}; }}"
            )
            self.btn_do_write.clicked.connect(self._on_write_log_qt)
            panel.addWidget(self.btn_do_write)
            self.frame_log_panel.setVisible(False)
            log_row.addWidget(self.frame_log_panel)

            self.lbl_testlog_status = QLabel("—")
            self.lbl_testlog_status.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
            log_row.addWidget(self.lbl_testlog_status)
            self.btn_open_testlog = QPushButton("Mở log")
            self.btn_open_testlog.setFixedHeight(_BTN_HEIGHT)
            self.btn_open_testlog.setFixedWidth(70)
            self.btn_open_testlog.setStyleSheet(
                f"QPushButton {{ background-color: {_BORDER}; color: {_TEXT}; border: 1px solid {_TEXT_MUTED}; "
                f"border-radius: {_BTN_RADIUS}px; font-size: 10px; }} QPushButton:hover {{ background-color: {_TEXT_MUTED}; color: {_BG_DARK}; }}"
            )
            self.btn_open_testlog.clicked.connect(self._on_open_testlog_qt)
            log_row.addWidget(self.btn_open_testlog)
            bottom_bar.addLayout(log_row)
            main_layout.addLayout(bottom_bar)

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._process_queue_qt)
            self._timer.start(100)
            self.log_signal.connect(self._append_log_qt)
            self.refresh_done_signal.connect(self._on_refresh_done_qt)
            QTimer.singleShot(600, self._refresh_stats_qt)
            QTimer.singleShot(400, self._update_testlog_status_qt)
            self._last_popup_epoch = 0.0

        def _update_testlog_status_qt(self):
            p = get_testlog_path()
            if p.exists():
                try:
                    size = p.stat().st_size
                    kb = max(1, int(round(size / 1024.0)))
                    self.lbl_testlog_status.setText(f"✓ {kb}KB")
                    self.lbl_testlog_status.setToolTip(str(p))
                except Exception:
                    self.lbl_testlog_status.setText("✓")
                    self.lbl_testlog_status.setToolTip(str(p))
            else:
                self.lbl_testlog_status.setText("—")
                self.lbl_testlog_status.setToolTip(str(p))

        def _toggle_log_panel_qt(self):
            try:
                visible = not self.frame_log_panel.isVisible()
                self.frame_log_panel.setVisible(visible)
                if visible:
                    self.btn_toggle_log.setText("Hủy")
                    self.spin_normal.setFocus()
                    self.spin_normal.selectAll()
                else:
                    self.btn_toggle_log.setText("Ghi log")
            except Exception:
                pass

        def _on_open_testlog_qt(self):
            p = get_testlog_path()
            target = p if p.exists() else p.parent
            if not target.exists() and not p.exists():
                target.mkdir(parents=True, exist_ok=True)
            try:
                if sys.platform == "win32":
                    os.startfile(str(target))
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(target)])
                else:
                    subprocess.Popen(["xdg-open", str(target)])
                self._log_qt("Đã mở: " + str(target))
            except Exception as e:
                self._log_qt("Không mở được: " + str(e), is_error=True)

        def _restart_app_qt(self):
            """Khá»Ÿi cháº¡y láº¡i chÆ°Æ¡ng trÃ¬nh (táº¯t vÃ  má»Ÿ láº¡i) Ä‘á»ƒ hiá»ƒn thá»‹ dá»¯ liá»‡u hiá»‡n táº¡i."""
            try:
                subprocess.Popen([sys.executable] + sys.argv, cwd=str(ROOT))
            except Exception:
                try:
                    subprocess.Popen([sys.executable, str(ROOT / "run_simulation_app.py")], cwd=str(ROOT))
                except Exception:
                    pass
            app = QApplication.instance()
            if app:
                app.quit()

        def _refresh_stats_qt(self):
            def work():
                try:
                    return load_stats_from_csv()
                except Exception:
                    return None
            def run():
                result = work()
                self.refresh_done_signal.emit(result)
            threading.Thread(target=run, daemon=True).start()

        def _on_refresh_done_qt(self, stats):
            try:
                if not stats:
                    return
                self.metric_logs.setText(f"{int(stats.get('logs_count', 0)):,}")
                self.metric_attacks.setText(f"{int(stats.get('attacks_count', 0)):,}")
                acc = stats.get("accuracy")
                self.metric_accuracy.setText(f"{float(acc):.1f}%" if acc is not None else "—")
                if stats.get("top_ip"):
                    c5 = stats.get("top_ip_count_5m") or 0
                    self.metric_topip.setText(f"{stats['top_ip']} ({c5}/5min)" if c5 else stats["top_ip"])
                else:
                    self.metric_topip.setText("—")
                self.metric_attack_today.setText(f"{int(stats.get('attack_today', 0)):,}")
                self.metric_attack_5m.setText(f"{int(stats.get('attack_5min', 0)):,}")
                self.lbl_logs.setText("Logs: " + f"{int(stats.get('logs_count', 0)):,}")
                self.lbl_attacks.setText("Attacks: " + f"{int(stats.get('attacks_count', 0)):,}")
                self.lbl_accuracy.setText("Score: " + (f"{float(acc):.1f}%" if acc is not None else "—"))
                self.lbl_topip.setText(
                    "Top IP: " + (stats.get("top_ip") or "—") + "  |  Attack 5m: " + f"{int(stats.get('attack_5min', 0)):,}"
                )
                ir = stats.get("ingestion_rate")
                self.lbl_ingestion_rate.setText("Ingest: " + (f"{ir} logs/min" if ir is not None else "—"))
                ar = stats.get("alert_rate")
                self.lbl_alert_rate.setText("Alert: " + (f"{ar} alerts/h" if ar is not None else "—"))
                self.lbl_model_ver.setText("Model version: " + (stats.get("model_version") or "—"))
                self.lbl_dataset_ver.setText("Dataset version: " + (stats.get("dataset_version") or "—"))
                if hasattr(self, "lbl_last_refresh"):
                    self.lbl_last_refresh.setText("Last refresh: " + datetime.now().strftime("%H:%M:%S"))
                hourly = stats.get("hourly_attacks") or [0] * 24
                hour_labels = stats.get("hour_labels") or None
                hourly_total = stats.get("hourly_total_alerts") or [0] * 24
                hourly_top_ip = stats.get("hourly_top_ip") or [None] * 24
                hourly_top_type = stats.get("hourly_top_attack_type") or [None] * 24
                hourly_avg_score = stats.get("hourly_avg_score") or [None] * 24
                hourly_top_model = stats.get("hourly_top_model") or [None] * 24
                if self.chart_container:
                    if getattr(self, "_preserve_attack_table_once", False):
                        # Preserve table content once (especially after Reset dữ liệu),
                        # to avoid blanking the table.
                        self._preserve_attack_table_once = False
                    else:
                        self._build_attack_table_qt(
                            hourly,
                            hour_labels=hour_labels,
                            hourly_total_alerts=hourly_total,
                            hourly_top_ip=hourly_top_ip,
                            hourly_top_attack_type=hourly_top_type,
                            hourly_avg_score=hourly_avg_score,
                            hourly_top_model=hourly_top_model,
                        )
            except Exception:
                pass

        def _clear_chart_container(self):
            try:
                layout = self.chart_container.layout() if self.chart_container else None
                if not layout:
                    return
                while layout.count():
                    item = layout.takeAt(0)
                    if item and item.widget():
                        item.widget().deleteLater()
            except Exception:
                pass

        def _clear_attack_table_qt(self):
            """Xóa nội dung Attack Hourly Table (nhưng không xóa log/model)."""
            try:
                self._preserve_attack_table_once = False
                self._clear_chart_container()
                if self.chart_container and self.chart_container.layout():
                    lbl = QLabel("Đã xóa dữ liệu bảng. Nhấn Refresh/Start để cập nhật lại.")
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setWordWrap(True)
                    lbl.setMinimumHeight(120)
                    lbl.setStyleSheet(
                        f"color: {_TEXT_MUTED}; font-size: 10px; background: {_BG_DARK}; border-radius: 6px; padding: 8px;"
                    )
                    self.chart_container.layout().addWidget(lbl)
            except Exception:
                pass

        def _build_chart_qt(self, hourly, hour_labels=None):
            try:
                if not HAS_QTCHARTS or not self.chart_container:
                    return
                self._clear_chart_container()
                # Khi không có dữ liệu tấn công trong 24h qua: hiển thị thông báo thay vì biểu đồ trống
                if not hourly or sum(hourly) == 0:
                    no_data = QLabel(
                        "Không có dữ liệu tấn công trong 24h qua.\n"
                        "Chạy Detection (mục 7) hoặc đảm bảo data/processed/logs.csv (hoặc predictions.csv) có bản ghi is_attack/ml_anomaly."
                    )
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    no_data.setWordWrap(True)
                    no_data.setMinimumHeight(120)
                    no_data.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px; background: {_BG_DARK}; border-radius: 6px; padding: 8px;")
                    self.chart_container.layout().addWidget(no_data)
                    return
                from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
                bar_set = QBarSet("Attacks")
                bar_set.append(hourly)
                bar_set.setColor(QColor(_ACCENT_GREEN))
                series = QBarSeries()
                series.append(bar_set)
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle("")
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                chart.setBackgroundBrush(QColor(_BG_DARK))
                chart.setPlotAreaBackgroundVisible(True)
                chart.setPlotAreaBackgroundBrush(QColor(_BG_CARD))
                # X-axis labels should match the same reference time window used to build `hourly`.
                if not hour_labels or len(hour_labels) != 24:
                    hour_labels = [(datetime.now() - timedelta(hours=23 - i)).strftime("%H") for i in range(24)]

                # Show fewer labels to keep the chart readable.
                categories = [(hour_labels[i] if i % 3 == 0 else "") for i in range(24)]
                axis_x = QBarCategoryAxis()
                axis_x.append(categories)
                axis_x.setLabelsAngle(-45)
                axis_x.setLabelsColor(QColor(_TEXT_MUTED))
                axis_x.setGridLineVisible(False)
                axis_x.setTitleText("")
                axis_font = QFont()
                axis_font.setPointSize(8)
                axis_x.setLabelsFont(axis_font)
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                axis_y = QValueAxis()
                axis_y.setRange(0, max(max(hourly, default=0), 1))
                axis_y.setLabelFormat("%d")
                axis_y.setLabelsColor(QColor(_TEXT_MUTED))
                axis_y.setGridLineColor(QColor(_BORDER))
                axis_y.setLinePenColor(QColor(_BORDER))
                axis_y.setLabelsFont(axis_font)
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
                chart.legend().setVisible(False)
                chart_view = QChartView(chart)
                chart_view.setMinimumHeight(170)
                chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
                chart_view.setStyleSheet("background: transparent;")
                self.chart_container.layout().addWidget(chart_view)
                self.chart_view = chart_view

                # Add a readable summary for non-zero hours.
                nonzero = [
                    (hour_labels[i], hourly[i])
                    for i in range(24)
                    if hourly[i] and hourly[i] > 0
                ]
                if nonzero:
                    shown = nonzero[:8]
                    extra = "" if len(nonzero) <= 8 else f" (+{len(nonzero) - 8} giờ khác)"
                    summary = "Khung giờ log có tấn công (event time, giờ VN): " + ", ".join([f"{h}: {v}" for h, v in shown]) + extra
                else:
                    summary = "Khung giờ log có tấn công (event time, giờ VN): —"
                sum_lbl = QLabel(summary)
                sum_lbl.setWordWrap(True)
                sum_lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px; padding: 6px 0;")
                self.chart_container.layout().addWidget(sum_lbl)
            except Exception:
                pass

        def _build_chart_text_qt(self, hourly, hour_labels=None):
            try:
                if not self.chart_container:
                    return
                self._clear_chart_container()
                if not hourly or sum(hourly) == 0:
                    no_data = QLabel("Không có dữ liệu tấn công trong 24h qua. Chạy Detection hoặc kiểm tra logs.csv / predictions.csv.")
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    no_data.setWordWrap(True)
                    no_data.setMinimumHeight(80)
                    no_data.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px; background: {_BG_DARK}; border-radius: 6px; padding: 8px;")
                    self.chart_container.layout().addWidget(no_data)
                    return
                if not hour_labels or len(hour_labels) != 24:
                    hour_labels = [(datetime.now() - timedelta(hours=23 - i)).strftime("%H") for i in range(24)]

                nonzero = [(hour_labels[i], v) for i, v in enumerate(hourly) if v and v > 0]
                if nonzero:
                    # Render compact list: "HH: v" only.
                    shown = nonzero[:12]
                    extra = "" if len(nonzero) <= 12 else f" (+{len(nonzero) - 12} giờ khác)"
                    text = "Khung giờ log có tấn công (event time, giờ VN): " + ", ".join([f"{h}: {v}" for h, v in shown]) + extra
                else:
                    text = "Khung giờ log có tấn công (event time, giờ VN): —"
                lbl = QLabel(text)
                lbl.setMinimumHeight(70)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(f"color: {_ACCENT_GREEN}; font-size: 11px; font-family: monospace; padding-top: 6px;")
                self.chart_container.layout().addWidget(lbl)
            except Exception:
                pass

        def _build_attack_table_qt(
            self,
            hourly,
            hour_labels=None,
            hourly_total_alerts=None,
            hourly_top_ip=None,
            hourly_top_attack_type=None,
            hourly_avg_score=None,
            hourly_top_model=None,
        ):
            """
            Replace the timeline chart with a readable table.
            Show only hours with attacks (>0) to avoid confusion.
            """
            try:
                if not self.chart_container:
                    return
                self._clear_chart_container()

                hourly = hourly or [0] * 24
                hourly_total_alerts = hourly_total_alerts or [0] * 24
                hourly_top_ip = hourly_top_ip or [None] * 24
                hourly_top_attack_type = hourly_top_attack_type or [None] * 24
                hourly_avg_score = hourly_avg_score or [None] * 24
                hourly_top_model = hourly_top_model or [None] * 24
                if len(hourly) != 24:
                    # Defensive fallback
                    hourly = list(hourly)[:24] + ([0] * 24)
                    hourly = hourly[:24]

                if not hour_labels or len(hour_labels) != 24:
                    hour_labels = [(datetime.now() - timedelta(hours=23 - i)).strftime("%H") for i in range(24)]

                total_attacks = sum(hourly)
                if total_attacks == 0:
                    no_data = QLabel("Không có tấn công trong 24h qua.\nThử chạy Detection để cập nhật dữ liệu.")
                    no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    no_data.setWordWrap(True)
                    no_data.setMinimumHeight(80)
                    no_data.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px; background: {_BG_DARK}; border-radius: 6px; padding: 8px;")
                    self.chart_container.layout().addWidget(no_data)
                    return

                nonzero_indices = [i for i in range(24) if hourly[i] and hourly[i] > 0]

                # Optional severity column for quick SOC-style risk scanning.
                table = QTableWidget(len(nonzero_indices), 8)
                table.setHorizontalHeaderLabels(["Khung giờ log (VN)", "#Tấn công", "Attack rate", "Top IP", "Top attack_type", "Avg score", "Top model", "Severity"])
                table.verticalHeader().setVisible(False)
                table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
                table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                table.setStyleSheet(
                    "QTableWidget { background: transparent; color: #c9d1d9; gridline-color: #21262d; }"
                    "QHeaderView::section { background: #161b22; color: #e2e8f0; padding: 6px; font-weight: 600; }"
                    "QTableWidget::item { padding: 6px; }"
                )

                for r, idx in enumerate(nonzero_indices):
                    h_raw = hour_labels[idx] if hour_labels and idx < len(hour_labels) else str(idx)
                    # Make the "Giờ" column clearer by showing the full 1-hour range.
                    # Example: "10:00-11:00" instead of just "10".
                    try:
                        h_int = int(str(h_raw).strip())
                        h = f"{h_int:02d}:00-{(h_int + 1) % 24:02d}:00"
                    except Exception:
                        h = str(h_raw)
                    v = hourly[idx]
                    total = hourly_total_alerts[idx] or 0
                    rate = (v / total * 100.0) if total else 0.0
                    top_ip = hourly_top_ip[idx] or "—"
                    top_type = hourly_top_attack_type[idx] or "—"
                    avg_score = hourly_avg_score[idx]
                    top_model = hourly_top_model[idx] or "—"
                    avg_score_str = f"{avg_score:.3f}" if isinstance(avg_score, (int, float)) else "—"
                    # Heuristic severity:
                    # - High: very high attack ratio or high average anomaly score
                    # - Medium: moderate ratio/score
                    # - Low: otherwise
                    if rate >= 80.0 or (isinstance(avg_score, (int, float)) and avg_score >= 0.7):
                        sev = "High"
                    elif rate >= 40.0 or (isinstance(avg_score, (int, float)) and avg_score >= 0.4):
                        sev = "Medium"
                    else:
                        sev = "Low"

                    table.setItem(r, 0, QTableWidgetItem(str(h)))
                    table.setItem(r, 1, QTableWidgetItem(str(int(v))))
                    table.setItem(r, 2, QTableWidgetItem(f"{rate:.1f}%"))
                    table.setItem(r, 3, QTableWidgetItem(str(top_ip)))
                    table.setItem(r, 4, QTableWidgetItem(str(top_type)))
                    table.setItem(r, 5, QTableWidgetItem(str(avg_score_str)))
                    table.setItem(r, 6, QTableWidgetItem(str(top_model)))
                    table.setItem(r, 7, QTableWidgetItem(sev))

                # Right-align numeric columns for readability.
                for r in range(len(nonzero_indices)):
                    for c in (1, 2, 5):
                        item = table.item(r, c)
                        if item:
                            item.setTextAlignment(int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))

                table.resizeColumnsToContents()
                table.setMinimumHeight(min(220, 30 + len(nonzero_indices) * 28))
                self.chart_container.layout().addWidget(table)
            except Exception:
                pass

        def _update_status_bar_qt(self):
            try:
                es_ok = check_elasticsearch()
                status = "ON" if es_ok else "OFF"
                color = _STATUS_OK if es_ok else _STATUS_FAIL
                self.lbl_es.setText("ES: " + status)
                self.lbl_es.setStyleSheet(f"color: {color}; font-size: 10px;")
                if hasattr(self, "metric_es_badge"):
                    self.metric_es_badge.setText("ES: ON" if es_ok else "ES: OFF")
                    self.metric_es_badge.setStyleSheet(
                        f"color: {'#9be9a8' if es_ok else '#ff7b72'}; background: {_BG_DARK}; "
                        f"border: 1px solid {'#2ea043' if es_ok else '#da3633'}; "
                        "border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 600;"
                    )
            except Exception:
                pass
            try:
                # Model status: support multiple training sources.
                unified_model = ROOT / "data" / "models" / "ssh_attack_model.joblib"
                kaggle_model = ROOT / "data" / "models" / "rf_ssh_random_forest.joblib"
                russell_model = ROOT / "data" / "models" / "rf_russellmitchell.joblib"
                custom_model = ROOT / "data" / "models" / "rf_custom.joblib"

                if unified_model.exists():
                    model_label = "Unified"
                    loaded = True
                elif kaggle_model.exists():
                    model_label = "Kaggle"
                    loaded = True
                elif russell_model.exists():
                    model_label = "Russell"
                    loaded = True
                elif custom_model.exists():
                    model_label = "Custom"
                    loaded = True
                else:
                    model_label = "OFF"
                    loaded = False

                color = _STATUS_OK if loaded else _STATUS_FAIL
                self.lbl_model.setText("Model: " + model_label)
                self.lbl_model.setStyleSheet(f"color: {color}; font-size: 10px;")
                if hasattr(self, "metric_model_badge"):
                    short_model = "Unified" if "Unified" in model_label else (
                        "Kaggle" if "Kaggle" in model_label else (
                            "Russell" if "Russell" in model_label else (
                                "Custom" if "Custom" in model_label else "—"
                            )
                        )
                    )
                    self.metric_model_badge.setText(f"Model: {short_model if loaded else 'OFF'}")
                    self.metric_model_badge.setStyleSheet(
                        f"color: {'#9be9a8' if loaded else '#ff7b72'}; background: {_BG_DARK}; "
                        f"border: 1px solid {'#2ea043' if loaded else '#da3633'}; "
                        "border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 600;"
                    )
            except Exception:
                pass
            try:
                ok_fb, out_fb = run_cmd_shell('tasklist /FI "IMAGENAME eq filebeat.exe"', timeout=10)
                fb_on = ok_fb and ("filebeat.exe" in (out_fb or "").lower())
                self.lbl_fb.setText("Filebeat: " + ("ON" if fb_on else "OFF"))
                self.lbl_fb.setStyleSheet(f"color: {(_STATUS_OK if fb_on else _STATUS_FAIL)}; font-size: 10px;")
                if hasattr(self, "metric_fb_badge"):
                    self.metric_fb_badge.setText("Filebeat: ON" if fb_on else "Filebeat: OFF")
                    self.metric_fb_badge.setStyleSheet(
                        f"color: {'#9be9a8' if fb_on else '#ff7b72'}; background: {_BG_DARK}; "
                        f"border: 1px solid {'#2ea043' if fb_on else '#da3633'}; "
                        "border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 600;"
                    )
            except Exception:
                self.lbl_fb.setText("Filebeat: —")
                self.lbl_fb.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")

        def _select_action_qt(self, action_str):
            self.selected_action = action_str
            for a, btn, _ in self.action_buttons:
                btn.setChecked(a == action_str)
            # Chỉ đổi visibility khi các frame đã được tạo (tránh lỗi khi gọi sớm trong __init__)
            scenario_action = (action_str or "").startswith("6.2 ")
            evaluate_action = (action_str or "").startswith("6.4 ")
            if hasattr(self, "frame_training_src"):
                # Train Custom CSV (handler: action startswith "6.2 ")
                self.frame_training_src.setVisible(scenario_action)
            if hasattr(self, "frame_csv"):
                # Evaluate Model / Train từ CSV (handler: action startswith "6.4 ")
                self.frame_csv.setVisible(evaluate_action)
            if hasattr(self, "frame_reset_opts"):
                # Reset options chỉ hiện khi bấm nút "Reset Data" (action id là "1. Reset ...").
                self.frame_reset_opts.setVisible((action_str or "") in ("Reset Data", "1. Reset dữ liệu (xóa index)"))
            if hasattr(self, "frame_scenario_custom"):
                rb = self.training_src_group.checkedButton() if hasattr(self, "training_src_group") else None
                src = rb.property("value") if rb else "synthetic"
                self.frame_scenario_custom.setVisible(scenario_action and src == "custom")

        def _on_scenario_src_toggled(self):
            if not hasattr(self, "frame_scenario_custom"):
                return
            rb = self.training_src_group.checkedButton()
            src = rb.property("value") if rb else "synthetic"
            scenario_action = (self.selected_action or "").startswith("6.2 ")
            self.frame_scenario_custom.setVisible(scenario_action and src == "custom")

        def _log_qt(self, msg, is_error=False):
            self.msg_queue.put(("log", msg, is_error))

        def _append_log_qt(self, text, is_error):
            self.txt.appendPlainText((text or "") + "\n")
            self.txt.verticalScrollBar().setValue(self.txt.verticalScrollBar().maximum())

        def _open_local_path_qt(self, target_path):
            try:
                target = Path(target_path)
                if not target.exists():
                    self._log_qt("Không tìm thấy file: " + str(target), is_error=True)
                    return False
                if sys.platform == "win32":
                    os.startfile(str(target))
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(target)])
                else:
                    subprocess.Popen(["xdg-open", str(target)])
                self._log_qt("Đã mở: " + str(target))
                return True
            except Exception as e:
                self._log_qt("Không mở được file báo cáo: " + str(e), is_error=True)
                return False

        def _show_popup_qt(self, title, body, level="info", report_path=""):
            try:
                box = QMessageBox(self)
                if level == "error":
                    box.setIcon(QMessageBox.Icon.Critical)
                elif level == "warning":
                    box.setIcon(QMessageBox.Icon.Warning)
                else:
                    box.setIcon(QMessageBox.Icon.Information)
                box.setWindowTitle(title or "ELKShield Alert")
                box.setText(body or "")
                open_btn = None
                if (report_path or "").strip():
                    open_btn = box.addButton("Xem báo cáo", QMessageBox.ButtonRole.ActionRole)
                box.addButton(QMessageBox.StandardButton.Ok)
                box.exec()
                if open_btn and box.clickedButton() == open_btn:
                    self._open_local_path_qt(report_path)
            except Exception:
                pass

        def _process_queue_qt(self):
            try:
                while True:
                    msg = self.msg_queue.get_nowait()
                    if msg[0] == "log":
                        self.log_signal.emit(msg[1] or "", msg[2])
                    elif msg[0] == "popup":
                        now_ts = datetime.now().timestamp()
                        if now_ts - float(getattr(self, "_last_popup_epoch", 0.0) or 0.0) >= 45.0:
                            self._last_popup_epoch = now_ts
                            self._show_popup_qt(
                                msg[1] if len(msg) > 1 else "ELKShield Alert",
                                msg[2] if len(msg) > 2 else "",
                                msg[3] if len(msg) > 3 else "info",
                                msg[4] if len(msg) > 4 else "",
                            )
                    elif msg[0] == "done":
                        self.btn_run.setEnabled(True)
            except queue.Empty:
                pass

        def _on_run_qt(self):
            if self.running:
                return
            self.running = True
            # Reset popup cooldown per run so each Detection can notify at least once.
            self._last_popup_epoch = 0.0
            self.btn_run.setEnabled(False)
            self.txt.clear()
            threading.Thread(target=self._run_worker_qt, daemon=True).start()

        def _run_worker_qt(self):
            action = self.selected_action
            if not action:
                self._log_qt("Chọn một thao tác (bấm vào nút bên trên).")
                self.running = False
                self.msg_queue.put(("done",))
                return
            try:
                self._do_action_qt(action)
            except Exception as e:
                self._log_qt(str(e), is_error=True)
            self.running = False
            self.msg_queue.put(("done",))

        def _on_write_log_qt(self):
            try:
                n = int(self.spin_normal.text().strip() or "2")
                a = int(self.spin_attack.text().strip() or "5")
            except ValueError:
                self._log_qt("Nhập số nguyên cho normal và attack.")
                return
            written = write_sample_log(max(0, n), max(0, a))
            if written:
                self._log_qt("Đã ghi " + str(n + a) + " dòng vào:\n" + "\n".join(written))
            else:
                self._log_qt("Không ghi được file.", is_error=True)
            self._update_testlog_status_qt()
            try:
                self.frame_log_panel.setVisible(False)
                self.btn_toggle_log.setText("Ghi log")
            except Exception:
                pass

        def _do_action_qt(self, action):
            if action == "1. Reset dữ liệu (xóa index)":
                if self.confirm_reset:
                    self._log_qt("Đang xóa index Elasticsearch (test-logs-*, ml-alerts-*)...")
                    ok1, out1 = delete_elasticsearch_indices("test-logs-*")
                    self._log_qt("test-logs-*: " + (out1 if ok1 else "lỗi " + out1))
                    ok2, out2 = delete_elasticsearch_indices("ml-alerts-*")
                    self._log_qt("ml-alerts-*: " + (out2 if ok2 else "lỗi " + out2))
                    if (ROOT / "reset_data_silent.bat").exists():
                        ok, out = run_cmd_shell("call reset_data_silent.bat", timeout=60)
                        self._log_qt(out)
                    elif (ROOT / "reset_data.bat").exists():
                        ok, out = run_cmd_shell("call reset_data.bat", timeout=60)
                        self._log_qt(out)
                    else:
                        self._log_qt("[Xong] Đã gọi lệnh xóa index.")
                    if self.reset_del_processed_cb.isChecked():
                        # Reset dữ liệu có thể làm bảng bị "trống" do files bị xóa.
                        # Giữ nguyên nội dung bảng Attack Hourly Table sau Reset một lần refresh.
                        self._preserve_attack_table_once = True
                        removed = []
                        for p in [
                            ROOT / "data" / "processed" / "logs.csv",
                            ROOT / "data" / "processed" / "russellmitchell_predictions.csv",
                            ROOT / "data" / "processed" / "custom_predictions.csv",
                            ROOT / "data" / "processed" / "predictions.csv",
                            ROOT / "data" / "predictions.csv",
                        ]:
                            if p.exists():
                                try:
                                    p.unlink()
                                    removed.append(str(p))
                                except Exception as e:
                                    self._log_qt(f"Không xóa được {p}: {e}", is_error=True)
                        if removed:
                            self._log_qt("Đã xóa dữ liệu đã xử lý: " + ", ".join(removed))
                        QTimer.singleShot(200, self._refresh_stats_qt)
                    if self.reset_del_model_cb.isChecked():
                        for d in [ROOT / "data" / "models"]:
                            if d.exists():
                                for f in d.glob("*.joblib"):
                                    try:
                                        f.unlink()
                                        self._log_qt("Đã xóa model: " + str(f))
                                    except Exception:
                                        pass
                    self.confirm_reset = False
                else:
                    self.confirm_reset = True
                    self._log_qt("Bấm Start Security Workflow lần nữa để xác nhận Reset Data.")

            elif action == "2. Má»Ÿ Filebeat (cá»­a sá»• má»›i)":
                fb_dir = ROOT / "config" / "filebeat"
                bat = fb_dir / "Chay_Filebeat.bat"
                if bat.exists():
                    try:
                        if sys.platform == "win32":
                            # Keep a dedicated cmd window open to diagnose startup errors.
                            subprocess.Popen(
                                ["cmd", "/k", "call Chay_Filebeat.bat"],
                                cwd=str(fb_dir),
                                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
                            )
                        else:
                            subprocess.Popen([str(bat)], cwd=str(fb_dir))
                        self._log_qt("Đã mở cửa sổ Filebeat.")
                        def _post_check():
                            self._update_status_bar_qt()
                            ok_fb2, out_fb2 = run_cmd_shell('tasklist /FI "IMAGENAME eq filebeat.exe"', timeout=10)
                            if not (ok_fb2 and ("filebeat.exe" in (out_fb2 or "").lower())):
                                self._log_qt(
                                    "Filebeat chưa chạy ổn định (có thể tự tắt). "
                                    "Kiểm tra cửa sổ Filebeat vừa mở để xem lỗi chi tiết.",
                                    is_error=True,
                                )
                        QTimer.singleShot(6000, _post_check)
                    except Exception as e:
                        self._log_qt(f"Không mở được Filebeat: {e}", is_error=True)
                else:
                    self._log_qt("Không tìm thấy config/filebeat/Chay_Filebeat.bat.", is_error=True)

            elif action == "3. Má»Ÿ Kibana":
                webbrowser.open("http://localhost:5601")
                ok, out = run_cmd_shell("curl -s http://127.0.0.1:9200/_cat/indices?v 2>nul", timeout=10)
                self._log_qt(out or "Kibana: http://localhost:5601")

            elif action == "15. Sync model":
                self._log_qt("Sync model: kiá»ƒm tra ES + model...")
                es_ok = check_elasticsearch()
                self._log_qt("Elasticsearch: " + ("OK" if es_ok else "Dừng"))
                model_path = ROOT / "data" / "models" / "ssh_attack_model.joblib"
                if model_path.exists():
                    try:
                        ver = "v1.0." + datetime.fromtimestamp(model_path.stat().st_mtime).strftime("%y%m%d")
                        self._log_qt("Model: đã đồng bộ (" + ver + ")")
                    except Exception:
                        self._log_qt("Model: đã tải")
                else:
                    self._log_qt("Model: chưa có. Chạy Train Global Model trước.")
                QTimer.singleShot(200, self._update_status_bar_qt)
                QTimer.singleShot(200, self._refresh_stats_qt)

            elif action == "Start SIEM":
                self._log_qt("Start Monitoring: Check ELK → Load Model → Collect Logs → Feature Extraction → ML Detection → Write Alert ES → Suggest Defense → Dashboard.")
                def _run_flow():
                    try:
                        from elkshield.flow import run_monitoring_flow
                        ok, msg = run_monitoring_flow(
                            log_callback=lambda t, m, e: self.msg_queue.put((t, m, e)),
                            open_browser=True,
                            write_test_log_first=True,
                        )
                        self.msg_queue.put(("log", "=== Hoàn tất: %s ===" % msg, not ok))
                        # Report latest alerts directly in-app (avoid forcing user to open Kibana).
                        try:
                            ok2, msg2, alerts = fetch_latest_alerts_from_es(limit=10, index_pattern="ml-alerts-*")
                            if ok2:
                                if not alerts:
                                    self.msg_queue.put(("log", "Không có cảnh báo mới trong index ml-alerts-*.", False))
                                else:
                                    attack_alerts = [a for a in alerts if _to_bool(a.get("is_attack", False))]
                                    if attack_alerts:
                                        self.msg_queue.put(("log", f"=== Alerts Report: CÓ TẤN CÔNG ({len(attack_alerts)}/{len(alerts)}) ===", False))
                                        lines = []
                                        for a in attack_alerts[:10]:
                                            ts = a.get("@timestamp") or a.get("timestamp") or "—"
                                            src = a.get("source_ip") or "—"
                                            atk_type = a.get("attack_type") or "unknown"
                                            ml_model = a.get("ml_model") or "—"
                                            score = a.get("ml_anomaly_score")
                                            rec = a.get("defense_recommendations") or "—"
                                            lines.append(f"{ts} | ATTACK | {src} | {atk_type} | score={score} | model={ml_model} | rec={rec}")
                                        self.msg_queue.put(("log", "\n".join(lines), False))
                                    else:
                                        self.msg_queue.put(("log", f"=== Alerts Report: KHÔNG PHÁT HIỆN TẤN CÔNG ({len(alerts)}/{len(alerts)} là NORMAL) ===", False))
                                        # Optionally show a few normal alerts for evidence.
                                        lines = []
                                        for a in alerts[:5]:
                                            ts = a.get("@timestamp") or a.get("timestamp") or "—"
                                            src = a.get("source_ip") or "—"
                                            atk_type = a.get("attack_type") or "—"
                                            ml_model = a.get("ml_model") or "—"
                                            score = a.get("ml_anomaly_score")
                                            lines.append(f"{ts} | NORMAL | {src} | {atk_type} | score={score} | model={ml_model}")
                                        self.msg_queue.put(("log", "\n".join(lines), False))
                            else:
                                self.msg_queue.put(("log", msg2, True))
                        except Exception as e:
                            self.msg_queue.put(("log", f"Lỗi tạo báo cáo alerts in-app: {e}", True))
                    except Exception as e:
                        self.msg_queue.put(("log", "Lỗi unified flow: %s. Chạy fallback script." % e, True))
                        # Fallback: cháº¡y script nhÆ° cÅ©
                        run_cmd_stream(
                            ["scripts/run_by_architecture.py", "--no-browser"],
                            str(ROOT), 1200, self.msg_queue.put,
                        )
                        webbrowser.open("http://localhost:5601/app/discover#/?_a=(index:ml-alerts)")
                threading.Thread(target=_run_flow, daemon=True).start()

            elif action == "6.1 Train UNIFIED (gá»™p dataset)":
                ok, out = run_cmd(["scripts/train_model.py"], timeout=900)
                self._log_qt(out or "(xong)", is_error=not ok)

            elif action == "6.2 Train Custom CSV":
                rb = self.training_src_group.checkedButton()
                src = rb.property("value") if rb else "custom"
                if src == "synthetic":
                    ok1, out1 = run_cmd(["scripts/generate_synthetic_logs.py", "--total", "8000", "--normal-ratio", "0.85", "--days", "14", "--replace-logs"], timeout=300)
                    if ok1:
                        ok2, out2 = run_cmd(["scripts/data_preprocessing.py", "--input", "data/raw/logs.csv", "--output", "data/processed/logs.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack"], timeout=120)
                        self._log_qt(out1 + "\n\n" + (out2 or "(xong)"))
                    else:
                        self._log_qt(out1, is_error=True)
                elif src == "russell":
                    if not (ROOT / "data" / "russellmitchell" / "gather").exists():
                        self._log_qt("Thư mục data/russellmitchell/gather không tồn tại.", is_error=True)
                    else:
                        for desc, args in [
                            ("Bước 1/4", ["scripts/russellmitchell_auth_to_csv.py", "--data-dir", "data/russellmitchell", "--output", "data/raw/russellmitchell_auth.csv", "--with-labels"]),
                            ("Bước 2/4", ["scripts/data_preprocessing.py", "--input", "data/raw/russellmitchell_auth.csv", "--output", "data/processed/russellmitchell_processed.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack", "--log-type", "ssh"]),
                            ("Bước 3/4", ["scripts/ml_detector.py", "--input", "data/processed/russellmitchell_processed.csv", "--train", "--model-type", "random_forest", "--model-file", "data/models/rf_russellmitchell.joblib", "--output", "data/processed/russellmitchell_predictions.csv", "--handle-imbalance"]),
                            ("Bước 4/4", ["scripts/elasticsearch_writer.py", "--input", "data/processed/russellmitchell_predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "russellmitchell"]),
                        ]:
                            ok, out = run_cmd(args, timeout=300)
                            self._log_qt(f"{desc}: " + (out or "(xong)"))
                            if not ok:
                                self._log_qt(out, is_error=True)
                                break
                elif src == "kaggle":
                    if not (ROOT / "data" / "ssh_anomaly_dataset.csv").exists():
                        self._log_qt("Chưa có file data/ssh_anomaly_dataset.csv.", is_error=True)
                    else:
                        self._log_qt("Train Scenario (Kaggle): pipeline đầy đủ...")
                        ok = run_cmd_stream(
                            ["scripts/run_pipeline_ssh.py", "--input", "data/ssh_anomaly_dataset.csv", "--kaggle", "--output-dir", "data", "--model-type", "random_forest"],
                            str(ROOT), 1800, self.msg_queue.put,
                        )
                        if not ok:
                            self._log_qt("Pipeline Kaggle kết thúc với lỗi hoặc timeout.", is_error=True)
                        # Update status bar model label right after Kaggle training.
                        QTimer.singleShot(200, self._update_status_bar_qt)
                elif src == "custom":
                    custom_path = (self.entry_scenario_custom.text() or "").strip()
                    if not custom_path or not (ROOT / custom_path).exists():
                        self._log_qt("Nhập đường dẫn tệp CSV (Custom) và đảm bảo file tồn tại.", is_error=True)
                    else:
                        self._log_qt("Train Scenario (Custom): preprocess → train → (ghi ES nếu chọn)...")
                        ok1, out1 = run_cmd(["scripts/data_preprocessing.py", "--input", custom_path, "--output", "data/processed/custom_processed.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack", "--log-type", "ssh"], timeout=120)
                        if ok1:
                            ok2, out2 = run_cmd(["scripts/ml_detector.py", "--input", "data/processed/custom_processed.csv", "--train", "--model-type", "random_forest", "--model-file", "data/models/rf_custom.joblib", "--output", "data/processed/custom_predictions.csv", "--handle-imbalance"], timeout=300)
                            self._log_qt(out2 or "(xong)", is_error=not ok2)
                            if ok2 and self.write_es_scenario_cb.isChecked():
                                ok3, out3 = run_cmd(["scripts/elasticsearch_writer.py", "--input", "data/processed/custom_predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "csv"], timeout=300)
                                self._log_qt("Ghi ES: " + (out3 or "(xong)"), is_error=not ok3)
                        else:
                            self._log_qt(out1 or "Preprocess tháº¥t báº¡i.", is_error=True)

            elif action == "6.4 Train tá»« CSV (Kaggle / tá»‡p)":
                rb = self.csv_group.checkedButton()
                val = rb.property("value") if rb else "B"
                custom_path = (self.entry_csv.text() or "").strip()
                write_es = self.write_es_cb.isChecked()
                if val == "B":
                    if (ROOT / "data" / "ssh_anomaly_dataset.csv").exists():
                        self._log_qt("Đang chạy pipeline Kaggle CSV (có thể mất vài phút)...")
                        ok = run_cmd_stream(
                            ["scripts/run_pipeline_ssh.py", "--input", "data/ssh_anomaly_dataset.csv", "--kaggle", "--output-dir", "data", "--model-type", "random_forest"],
                            str(ROOT),
                            1800,
                            self.msg_queue.put,
                        )
                        if not ok:
                            self._log_qt("Pipeline Kaggle kết thúc với lỗi hoặc timeout.", is_error=True)
                    else:
                        self._log_qt("Chưa có file data/ssh_anomaly_dataset.csv.", is_error=True)
                elif val == "C" and custom_path and (ROOT / custom_path).exists():
                    ok, out = run_cmd(["scripts/data_preprocessing.py", "--input", custom_path, "--output", "data/processed/custom_processed.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack", "--log-type", "ssh"])
                    if ok:
                        ok, out = run_cmd(["scripts/ml_detector.py", "--input", "data/processed/custom_processed.csv", "--train", "--model-type", "random_forest", "--model-file", "data/models/rf_custom.joblib", "--output", "data/processed/custom_predictions.csv", "--handle-imbalance"], timeout=300)
                    if ok and write_es:
                        ok, out = run_cmd(["scripts/elasticsearch_writer.py", "--input", "data/processed/custom_predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "csv"])
                    self._log_qt(out or "(xong)", is_error=not ok)
                else:
                    self._log_qt("Chọn Kaggle hoặc nhập đường dẫn tệp CSV (C).", is_error=True)

            elif action == "17. Model Explainability":
                self._log_qt("Model Explainability (Explainable AI):")
                self._log_qt("  • Mô hình: Random Forest — feature importance có thể xuất từ scripts/ml_detector.py (--metrics-output).")
                self._log_qt("  • Phát hiện: nhãn is_attack / ml_anomaly kèm theo log → để truy vết nguyên nhân.")
                self._log_qt("  • Timeline 24h + Defense Plan: hỗ trợ giải thích bối cảnh tấn công và đề xuất phòng thủ.")
                explain_doc = ROOT / "docs" / "ARCHITECTURE_RESEARCH.md"
                if explain_doc.exists():
                    self._log_qt("  • Chi tiết kiến trúc: docs/ARCHITECTURE_RESEARCH.md")

            elif action == "7. Detection online (→ ml-alerts)":
                # Auto-combine mode: ensure Filebeat is running and generate one fresh log line
                # so ingest path (Filebeat -> Logstash -> ES) has a recent event to pick up.
                try:
                    ok_fb, out_fb = run_cmd_shell('tasklist /FI "IMAGENAME eq filebeat.exe"', timeout=10)
                    fb_running = ok_fb and ("filebeat.exe" in (out_fb or "").lower())
                except Exception:
                    fb_running = False
                if not fb_running:
                    fb_dir = ROOT / "config" / "filebeat"
                    bat = fb_dir / "Chay_Filebeat.bat"
                    if bat.exists():
                        try:
                            if sys.platform == "win32":
                                subprocess.Popen(
                                    ["cmd", "/k", "call Chay_Filebeat.bat"],
                                    cwd=str(fb_dir),
                                    creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
                                )
                            else:
                                subprocess.Popen([str(bat)], cwd=str(fb_dir))
                            self._log_qt("Không thấy Filebeat đang chạy -> đã tự mở Chay_Filebeat.bat.")
                            QTimer.singleShot(6000, self._update_status_bar_qt)
                        except Exception as e:
                            self._log_qt(f"Không mở được Filebeat: {e}", is_error=True)
                    else:
                        self._log_qt("Không thấy Filebeat đang chạy và không tìm thấy Chay_Filebeat.bat.", is_error=True)
                try:
                    probe_ts = datetime.now().strftime("%b %d %H:%M:%S")
                    probe_line = f"{probe_ts} localhost sshd[9999]: Accepted password for probe from 192.168.1.250 port 22 ssh2"
                    p = get_testlog_path()
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with open(p, "a", encoding="utf-8", errors="replace") as f:
                        f.write(probe_line + "\n")
                    self._log_qt("Đã ghi 1 dòng probe vào test.log để kích hoạt ingest.")
                    import time
                    time.sleep(6)
                except Exception as e:
                    self._log_qt(f"Không ghi được dòng probe test.log: {e}", is_error=True)

                # Preflight checklist: source log indices in ES
                es_src_ok, es_src_msg, _ = check_source_log_indices()
                if es_src_ok:
                    self._log_qt("Preflight ES: " + es_src_msg)
                else:
                    self._log_qt("Preflight ES: " + es_src_msg, is_error=True)
                    self._log_qt(
                        "Checklist ingest: (1) chạy docker/logstash, (2) mở Filebeat và giữ cửa sổ mở, "
                        "(3) ghi thêm dòng mới vào test.log, (4) nếu cần xóa registry filebeat rồi chạy lại. "
                        "Detection vẫn chạy với fallback test.log.",
                        is_error=False,
                    )

                unified_model = ROOT / "data" / "models" / "ssh_attack_model.joblib"
                kaggle_model = ROOT / "data" / "models" / "rf_ssh_random_forest.joblib"
                if unified_model.exists():
                    model_path = unified_model
                    model_name = "unified"
                elif kaggle_model.exists():
                    model_path = kaggle_model
                    model_name = "kaggle"
                else:
                    self._log_qt(
                        "Chưa có model để Detection online. "
                        "Chạy [6.1] Train UNIFIED hoặc Train Scenario (Kaggle) để tạo rf_ssh_random_forest.joblib.",
                        is_error=True,
                    )
                    model_path = None

                if model_path:
                    run_id = datetime.utcnow().strftime("%H%M%S") + "-" + uuid.uuid4().hex[:6]
                    current_run_index_pattern = f"ml-alerts-*-{run_id}"
                    ok = run_cmd_stream(
                        [
                            "scripts/run_pipeline_detection.py",
                            "--model-file",
                            str(model_path),
                            "--model-name",
                            model_name,
                            "--run-id",
                            run_id,
                        ],
                        str(ROOT),
                        600,
                        self.msg_queue.put,
                    )
                    if not ok:
                        self._log_qt("Detection kết thúc với lỗi hoặc timeout.", is_error=True)
                    else:
                        # After detection ends, report alerts immediately in-app.
                        try:
                            report_source = "Elasticsearch"
                            ok2, msg2, alerts = fetch_latest_alerts_from_es(
                                limit=30,
                                index_pattern=current_run_index_pattern,
                                model_name=model_name,
                            )
                            # ES is near real-time; retry briefly before falling back to CSV.
                            if ok2 and not alerts:
                                import time
                                for _ in range(3):
                                    time.sleep(2)
                                    ok2, msg2, alerts = fetch_latest_alerts_from_es(
                                        limit=30,
                                        index_pattern=current_run_index_pattern,
                                        model_name=model_name,
                                    )
                                    if alerts:
                                        break
                            if (not ok2) or (not alerts):
                                # ES có thể tắt / index chưa sẵn. Fallback giống run detection.
                                if not ok2:
                                    self.msg_queue.put(("log", msg2, True))
                                ok3, msg3, alerts2 = fetch_latest_alerts_from_predictions_csv(limit=10, model_name=model_name)
                                if not ok3:
                                    # Nếu fallback cũng không được, báo lại trạng thái cũ.
                                    self.msg_queue.put(("log", msg3 or msg2, True))
                                    return
                                alerts = alerts2
                                report_source = "predictions.csv (fallback)"
                                self.msg_queue.put(("log", msg3, False))

                            ml_attack_alerts = []
                            rule_attack_alerts = []
                            if not alerts:
                                self.msg_queue.put(("log", "Detection xong: không có cảnh báo (fallback cũng không có).", False))
                            else:
                                # IMPORTANT:
                                # - ML result: ml_anomaly (model prediction)
                                # - Rule/label hint: is_attack (parsed/rule-enriched field)
                                ml_attack_alerts = [a for a in alerts if _to_bool(a.get("ml_anomaly", False))]
                                rule_attack_alerts = [a for a in alerts if _to_bool(a.get("is_attack", False))]
                                ml_status = (
                                    f"ML Alert: CÓ ({len(ml_attack_alerts)}/{len(alerts)})"
                                    if ml_attack_alerts
                                    else f"ML Alert: KHÔNG ({len(ml_attack_alerts)}/{len(alerts)})"
                                )
                                rule_status = (
                                    f"Rule Warning: CÓ ({len(rule_attack_alerts)}/{len(alerts)})"
                                    if rule_attack_alerts
                                    else f"Rule Warning: KHÔNG ({len(rule_attack_alerts)}/{len(alerts)})"
                                )
                                self.msg_queue.put(("log", f"Detection xong: {ml_status} | {rule_status}.", False))
                                # One-line decision for non-technical reviewers.
                                if ml_attack_alerts:
                                    decision = "Decision: ATTACK DETECTED (ML confirmed)"
                                elif rule_attack_alerts:
                                    decision = "Decision: NO ML ATTACK (RULE WARNING ONLY)"
                                else:
                                    decision = "Decision: NO ATTACK DETECTED"
                                self.msg_queue.put(("log", decision, False))

                                # Show only Top-3 priority alerts to keep terminal concise.
                                def _score_of(doc):
                                    try:
                                        return float(doc.get("ml_anomaly_score", 0) or 0)
                                    except Exception:
                                        return 0.0
                                priority_pool = ml_attack_alerts if ml_attack_alerts else (rule_attack_alerts if rule_attack_alerts else alerts)
                                top_priority = sorted(priority_pool, key=_score_of, reverse=True)[:3]
                                if top_priority:
                                    lines = []
                                    top_alert_objs = []
                                    for a in top_priority:
                                        ts = a.get("@timestamp") or a.get("timestamp") or "—"
                                        src = a.get("source_ip") or "—"
                                        atk_type = a.get("attack_type") or "unknown"
                                        ml_model = a.get("ml_model") or "—"
                                        score = a.get("ml_anomaly_score")
                                        rec = a.get("defense_recommendations") or "—"
                                        lbl = "RULE_ATTACK" if _to_bool(a.get("is_attack", False)) else "RULE_NORMAL"
                                        ml_lbl = "ML_ATTACK" if _to_bool(a.get("ml_anomaly", False)) else "ML_NORMAL"
                                        lines.append(
                                            f"{ts} | {ml_lbl} | {lbl} | {src} | {atk_type} | score={score} | model={ml_model} | rec={rec}"
                                        )
                                        top_alert_objs.append(
                                            {
                                                "timestamp": ts,
                                                "source_ip": src,
                                                "attack_type": atk_type,
                                                "ml_model": ml_model,
                                                "ml_anomaly_score": score,
                                                "ml_label": ml_lbl,
                                                "rule_label": lbl,
                                                "defense_recommendations": rec,
                                            }
                                        )
                                    self.msg_queue.put(("log", "Top-3 alerts:\n" + "\n".join(lines), False))
                                else:
                                    top_alert_objs = []

                                # Defense checklist (deduplicated from recommendations).
                                defense_items = []
                                for a in top_priority:
                                    rec = (a.get("defense_recommendations") or "").strip()
                                    if not rec:
                                        continue
                                    parts = [x.strip(" -•\t") for x in rec.replace("|", ";").split(";")]
                                    for p in parts:
                                        if p:
                                            defense_items.append(p)
                                dedup = []
                                seen = set()
                                for item in defense_items:
                                    k = item.lower()
                                    if k in seen:
                                        continue
                                    seen.add(k)
                                    dedup.append(item)
                                if dedup:
                                    checklist = "\n".join([f"[ ] {x}" for x in dedup[:5]])
                                    self.msg_queue.put(("log", "Defense checklist:\n" + checklist, False))
                                checklist_items = dedup[:5] if dedup else []

                                # Incident report file (date-time formatted) for traceability/demo.
                                report_ok, report_path_or_err = write_incident_report(
                                    report_source=report_source,
                                    model_name=model_name,
                                    run_index_pattern=current_run_index_pattern,
                                    decision=decision,
                                    total_records=len(alerts),
                                    ml_count=len(ml_attack_alerts),
                                    rule_count=len(rule_attack_alerts),
                                    top_alerts=top_alert_objs,
                                    defense_checklist=checklist_items,
                                )
                                if report_ok:
                                    self.msg_queue.put(("log", f"Incident report saved: {report_path_or_err}", False))
                                else:
                                    self.msg_queue.put(("log", f"Không ghi được incident report: {report_path_or_err}", True))

                                if not ml_attack_alerts:
                                    self.msg_queue.put(("log", "Detection xong: KHÔNG PHÁT HIỆN ML anomaly.", False))

                                # Popup alerts:
                                # - Trigger on ML anomalies.
                                # - If current preview misses anomalies (fallback preview window),
                                #   check full predictions.csv so important alerts are not lost.
                                effective_total = len(alerts)
                                effective_ml = len(ml_attack_alerts)
                                effective_rule = len(rule_attack_alerts)
                                popup_top_ip = None
                                if alerts:
                                    ip_counts = defaultdict(int)
                                    for a in alerts:
                                        ip = (a.get("source_ip") or "").strip()
                                        if ip:
                                            ip_counts[ip] += 1
                                    popup_top_ip = max(ip_counts, key=ip_counts.get) if ip_counts else None

                                if report_source.startswith("predictions.csv") and effective_ml == 0:
                                    ok_sum, _msg_sum, t_sum, ml_sum, rule_sum, top_ip_sum = summarize_predictions_csv(model_name=model_name)
                                    if ok_sum:
                                        effective_total = t_sum
                                        effective_ml = ml_sum
                                        effective_rule = rule_sum
                                        popup_top_ip = top_ip_sum or popup_top_ip

                                if effective_ml > 0:
                                    popup_msg = (
                                        f"ML attack detected: {effective_ml}/{effective_total}\n"
                                        f"Rule warnings: {effective_rule}/{effective_total}\n"
                                        f"Top IP: {popup_top_ip or '—'}\n"
                                        f"Report: {report_path_or_err if report_ok else 'not saved'}\n"
                                        "Xem Terminal Output để biết chi tiết."
                                    )
                                    self.msg_queue.put((
                                        "popup",
                                        "ELKShield Alert",
                                        popup_msg,
                                        "warning",
                                        report_path_or_err if report_ok else "",
                                    ))

                            # Executive summary block for quick review/presentation.
                            final_status = "SUCCESS" if ok else "FAILED"
                            summary_lines = [
                                "=== EXECUTIVE SUMMARY ===",
                                f"Source: {report_source}",
                                f"Records shown: {len(alerts)}",
                                f"ML anomalies: {len(ml_attack_alerts)}/{len(alerts) if alerts else 0}",
                                f"Rule attacks: {len(rule_attack_alerts)}/{len(alerts) if alerts else 0}",
                                f"Run index: {current_run_index_pattern}",
                                f"Final status: {final_status}",
                            ]
                            self.msg_queue.put(("log", "\n".join(summary_lines), final_status != "SUCCESS"))
                        except Exception as e:
                            self.msg_queue.put(("log", f"Lỗi tạo báo cáo alerts in-app sau Detection: {e}", True))

            elif action == "8. Demo nhanh (chá»‰ Python)":
                ok, out = run_cmd(["scripts/demo_quick.py"], timeout=300)
                self._log_qt(out or "(xong)", is_error=not ok)

            elif action == "9. Cháº¡y nhanh: log â†’ pipeline â†’ Kibana":
                write_sample_log(2, 5)
                self._log_qt("Đã ghi log mẫu. Đợi 15s...")
                import time
                time.sleep(15)
                for step, args in [
                    ("Bước 1", ["scripts/data_extraction.py", "--index", "test-logs-*,ssh-logs-*,filebeat-*,logstash-*,logs-*", "--output", "data/raw/logs.csv", "--hours", "8760", "--host", "127.0.0.1", "--port", "9200"]),
                    ("Bước 2", ["scripts/data_preprocessing.py", "--input", "data/raw/logs.csv", "--output", "data/processed/logs.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack"]),
                    ("Bước 3", ["scripts/ml_detector.py", "--input", "data/processed/logs.csv", "--train", "--model-type", "isolation_forest", "--model-file", "data/models/rf_ssh_isolation_forest.joblib", "--output", "data/predictions.csv"]),
                    ("Bước 4", ["scripts/elasticsearch_writer.py", "--input", "data/predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "synthetic"]),
                ]:
                    ok, out = run_cmd(args, timeout=300)
                    self._log_qt(step + ": " + (out or "(xong)"))
                    if not ok:
                        break
                webbrowser.open("http://localhost:5601")
                self._log_qt("Chạy nhanh xong. Kibana đã mở.")

            elif action == "Alert Feed":
                webbrowser.open("http://localhost:5601/app/discover#/?_a=(index:ml-alerts)")
                self._log_qt("Mở Kibana Discover (index ml-alerts) + báo cáo alerts trong app...")
                def _feed_alerts():
                    ok2, msg2, alerts = fetch_latest_alerts_from_es(limit=10, index_pattern="ml-alerts-*")
                    if (not ok2) or (not alerts):
                        if not ok2:
                            self.msg_queue.put(("log", msg2, True))
                        ok3, msg3, alerts2 = fetch_latest_alerts_from_predictions_csv(limit=10, model_name="—")
                        if ok3 and alerts2:
                            self.msg_queue.put(("log", msg3, False))
                            alerts = alerts2
                        else:
                            self.msg_queue.put(("log", "Không có cảnh báo mới trong ml-alerts-* (fallback predictions cũng không có).", False))
                            return
                    ml_attack_alerts = [a for a in alerts if _to_bool(a.get("ml_anomaly", False))]
                    rule_attack_alerts = [a for a in alerts if _to_bool(a.get("is_attack", False))]
                    ml_status = (
                        f"ML Alert: CÓ ({len(ml_attack_alerts)}/{len(alerts)})"
                        if ml_attack_alerts
                        else f"ML Alert: KHÔNG ({len(ml_attack_alerts)}/{len(alerts)})"
                    )
                    rule_status = (
                        f"Rule Warning: CÓ ({len(rule_attack_alerts)}/{len(alerts)})"
                        if rule_attack_alerts
                        else f"Rule Warning: KHÔNG ({len(rule_attack_alerts)}/{len(alerts)})"
                    )
                    self.msg_queue.put(("log", f"=== In-app Alerts Report: {ml_status} | {rule_status} ===", False))

                    lines = []
                    preview = ml_attack_alerts[:10] if ml_attack_alerts else alerts[:5]
                    for a in preview:
                        ts = a.get("@timestamp") or a.get("timestamp") or "—"
                        src = a.get("source_ip") or "—"
                        atk_type = a.get("attack_type") or "unknown"
                        ml_model = a.get("ml_model") or "—"
                        score = a.get("ml_anomaly_score")
                        rec = a.get("defense_recommendations") or "—"
                        lbl = "RULE_ATTACK" if _to_bool(a.get("is_attack", False)) else "RULE_NORMAL"
                        ml_lbl = "ML_ATTACK" if _to_bool(a.get("ml_anomaly", False)) else "ML_NORMAL"
                        lines.append(f"{ts} | {ml_lbl} | {lbl} | {src} | {atk_type} | score={score} | model={ml_model} | rec={rec}")
                    if lines:
                        self.msg_queue.put(("log", "\n".join(lines), False))
                threading.Thread(target=_feed_alerts, daemon=True).start()

            elif action in ("System Health", "Attack Analysis"):
                self._log_qt("--- Trạng thái hệ thống ---")
                es_ok = check_elasticsearch()
                self._log_qt("Elasticsearch : " + ("Đang chạy" if es_ok else "Dừng"))
                kibana_ok = check_kibana()
                self._log_qt("Kibana : " + ("Đang chạy (http://localhost:5601)" if kibana_ok else "Dừng"))
                model_path = ROOT / "data" / "models" / "ssh_attack_model.joblib"
                self._log_qt("Mô hình (ssh_attack_model) : " + ("Đã tải" if model_path.exists() else "Không tìm thấy"))
                p = get_testlog_path()
                if p.exists():
                    try:
                        size = p.stat().st_size
                        self._log_qt("test.log : Đã có (" + str(p) + ", " + str(size) + " bytes)")
                    except Exception:
                        self._log_qt("test.log : Đã có (" + str(p) + ")")
                else:
                    self._log_qt("test.log : Chưa có (" + str(p) + ")")
                fb_yml = ROOT / "config" / "filebeat" / "filebeat.yml"
                fb_bat = ROOT / "config" / "filebeat" / "Chay_Filebeat.bat"
                self._log_qt("Filebeat (config) : " + ("Có (filebeat.yml + Chay_Filebeat.bat)" if (fb_yml.exists() and fb_bat.exists()) else "Thiếu config"))
                logs_csv = ROOT / "data" / "processed" / "logs.csv"
                if logs_csv.exists():
                    try:
                        with open(logs_csv, "r", encoding="utf-8", errors="replace") as f:
                            n = sum(1 for _ in f) - 1
                        self._log_qt("data/processed/logs.csv : Có (" + str(n) + " dòng dữ liệu)")
                    except Exception:
                        self._log_qt("data/processed/logs.csv : Có")
                else:
                    self._log_qt("data/processed/logs.csv : Chưa có")
                raw_dir = ROOT / "data" / "raw"
                self._log_qt("data/raw : " + ("Có thư mục" if raw_dir.is_dir() else "Chưa có"))
                models_dir = ROOT / "data" / "models"
                if models_dir.is_dir():
                    joblibs = list(models_dir.glob("*.joblib"))
                    if joblibs:
                        self._log_qt("Model files : " + ", ".join(f.name for f in joblibs[:8]) + (" ..." if len(joblibs) > 8 else ""))
                    else:
                        self._log_qt("Model files : (trống)")
                else:
                    self._log_qt("Model files : (chưa có thư mục)")
                if es_ok:
                    ok, out = run_cmd_shell("curl -s http://127.0.0.1:9200/_cat/indices?v 2>nul", timeout=10)
                    self._log_qt(out or "(không có output)")
                self._log_qt("[Xong]")

            elif action == "12. Stack Management":
                webbrowser.open("http://localhost:5601/app/management/data/index_management/indices")
                self._log_qt("Đã mở Kibana Index Management (xem index).")

            elif action in ("Defense Plan", "13. Xem Đề xuất phòng thủ"):
                self._show_defense_recommendations_qt()

        def _show_defense_recommendations_qt(self):
            """Äá»c káº¿t quáº£ detection (predictions) vÃ  hiá»ƒn thá»‹ Ä‘á» xuáº¥t phÃ²ng thá»§ theo loáº¡i táº¥n cÃ´ng."""
            pred_files = [
                ROOT / "data" / "predictions.csv",
                ROOT / "data" / "processed" / "predictions.csv",
                ROOT / "data" / "processed" / "russellmitchell_predictions.csv",
                ROOT / "data" / "processed" / "custom_predictions.csv",
            ]
            csv_path = None
            for p in pred_files:
                if p.exists():
                    csv_path = p
                    break
            if not csv_path:
                self._log_qt("Chưa có file predictions. Chạy Detection (mục 7) trước.", is_error=True)
                return
            try:
                from scripts.defense_recommendations import get_recommendations, format_recommendations_text
            except ImportError:
                try:
                    from defense_recommendations import get_recommendations, format_recommendations_text
                except ImportError:
                    self._log_qt("Không tìm thấy module defense_recommendations.", is_error=True)
                    return
            lines = []
            seen_types = set()
            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    self._log_qt("File predictions rỗng hoặc không đúng format.", is_error=True)
                    return
                for row in reader:
                    is_anomaly = (
                        str(row.get("ml_anomaly", "")).strip().lower() in ("true", "1", "yes")
                        or str(row.get("prediction", "")).strip().lower() in ("true", "1", "yes")
                        or str(row.get("is_attack", "")).strip().lower() == "true"
                    )
                    if not is_anomaly:
                        continue
                    at = (row.get("attack_type") or "").strip() or "unknown"
                    if at not in seen_types:
                        seen_types.add(at)
                        lines.append("--- Đề xuất phòng thủ (loại: %s) ---" % (at or "unknown"))
                        lines.append(format_recommendations_text(at, "high"))
                        lines.append("")
            if not lines:
                lines.append("Không có bản ghi bất thường trong file predictions, hoặc chưa chạy Detection.")
                lines.append("Đề xuất mẫu (unknown):")
                lines.append(format_recommendations_text("unknown", "high"))
            self._log_qt("\n".join(lines))


if __name__ == "__main__":
    if HAS_QT:
        app = QApplication(sys.argv)
        win = SimulationAppQt()
        win.show()
        sys.exit(app.exec())
    else:
        print("Cần cài PySide6: pip install PySide6")
        sys.exit(1)

