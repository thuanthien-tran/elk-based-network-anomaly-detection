#!/usr/bin/env python3
"""
ELKShield - Ứng dụng desktop mô phỏng (SOC dashboard).
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
        QSizePolicy,
    )
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtGui import QColor, QPainter
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
        r = subprocess.run(
            [sys.executable] + list(args),
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
        queue_put(("log", "[Timeout] Lệnh chạy quá thời gian.", True))
        return False
    except Exception as e:
        queue_put(("log", str(e), True))
        return False


def load_stats_from_csv():
    """Đọc thống kê từ data/processed/logs.csv. Trả về dict: logs_count, attacks_count, accuracy, top_ip, top_ip_count_5m, attack_today, attack_5min, hourly_attacks (24 giá trị)."""
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
    }
    if not csv_path.exists():
        return out
    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_5m = now - timedelta(minutes=5)
        attack_counts_by_ip = defaultdict(int)
        attack_counts_by_ip_5m = defaultdict(int)
        hour_counts = defaultdict(int)
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return out
            for row in reader:
                out["logs_count"] += 1
                is_attack = str(row.get("is_attack", "")).strip().lower() == "true"
                if is_attack:
                    out["attacks_count"] += 1
                    src = (row.get("source_ip") or "").strip()
                    if src:
                        attack_counts_by_ip[src] += 1
                ts_str = (row.get("timestamp") or "").strip()
                if ts_str:
                    try:
                        ts = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
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
                    except Exception:
                        pass
        if attack_counts_by_ip:
            out["top_ip"] = max(attack_counts_by_ip, key=attack_counts_by_ip.get)
        if attack_counts_by_ip_5m:
            top = max(attack_counts_by_ip_5m, key=attack_counts_by_ip_5m.get)
            out["top_ip_count_5m"] = attack_counts_by_ip_5m[top]
        for i in range(24):
            t = (now - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
            out["hourly_attacks"][i] = hour_counts.get(t, 0)
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


def _glob_indices(pattern: str, names: list) -> list:
    """Lọc danh sách tên index theo pattern (vd: ml-alerts-* -> bắt đầu bằng ml-alerts-)."""
    import fnmatch
    return [n for n in names if fnmatch.fnmatch(n, pattern)]


def delete_elasticsearch_indices(pattern: str, host: str = "127.0.0.1", port: int = 9200):
    """Liệt kê index khớp pattern rồi xóa từng cái (ES có thể không xóa được khi DELETE trực tiếp wildcard)."""
    import urllib.request
    base = f"http://{host}:{port}"
    deleted = []
    errors = []
    try:
        # Thử _cat/indices/<pattern>; nếu 404 hoặc rỗng thì lấy toàn bộ rồi lọc
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
    """Đường dẫn file test.log trong thư mục Documents (cùng chỗ Ghi test.log ghi vào)."""
    import tempfile
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME") or tempfile.gettempdir()
    return Path(user) / "Documents" / "test.log"


def write_sample_log(normal: int, attack: int):
    import tempfile
    user = os.environ.get("USERPROFILE") or os.environ.get("HOME") or tempfile.gettempdir()
    lines = []
    for i in range(1, normal + 1):
        lines.append(f"Jan 19 10:00:{i:02d} localhost sshd[100{i}]: Accepted password for user{i} from 192.168.1.{10+i} port 22 ssh2")
    for j in range(1, attack + 1):
        lines.append(f"Jan 19 10:01:{j:02d} localhost sshd[20{j:02d}]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2")
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

            # Layout constants (gọn)
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
            main_layout.addWidget(status_pill)
            QTimer.singleShot(500, self._update_status_bar_qt)

            # 3) Dòng filter/stats: Log đã xử lý, Tấn công, Độ chính xác, IP / Tấn công (5 phút)
            stats_row = QHBoxLayout()
            stats_row.setSpacing(12)
            self.lbl_logs = QLabel("Log đã xử lý: —")
            self.lbl_attacks = QLabel("Tấn công phát hiện: —")
            self.lbl_accuracy = QLabel("Độ chính xác mô hình: —")
            self.lbl_topip = QLabel("IP tấn công hàng đầu: —  Tấn công (5 phút): —")
            for l in (self.lbl_logs, self.lbl_attacks, self.lbl_accuracy, self.lbl_topip):
                l.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
                stats_row.addWidget(l)
            stats_row.addStretch()
            main_layout.addLayout(stats_row)

            _CARD_STYLE = f"QFrame#card {{ background-color: {_BG_CARD}; border: 1px solid {_BORDER}; border-radius: {_CARD_RADIUS}px; }}"

            # 4) Phần trên: 2 cột — Logs Processed | Terminal Output
            top_row = QHBoxLayout()
            top_row.setSpacing(_CARD_GAP)

            # Trái: Logs Processed (thống kê đầy đủ + status)
            logs_card = QFrame()
            logs_card.setObjectName("card")
            logs_card.setStyleSheet(_CARD_STYLE)
            logs_card.setMinimumWidth(300)
            logs_inner = QVBoxLayout(logs_card)
            logs_inner.setContentsMargins(_CARD_PAD, _CARD_PAD, _CARD_PAD, _CARD_PAD)
            logs_inner.setSpacing(6)
            logs_head = QHBoxLayout()
            logs_title = QLabel("📄 Logs Processed")
            logs_title.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {_TEXT};")
            logs_head.addWidget(logs_title)
            logs_head.addStretch()
            self.btn_refresh = QPushButton("🔄 Làm mới")
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
            logs_inner.addLayout(stat_row("Logs Processed:", self.metric_logs))
            logs_inner.addLayout(stat_row("Attacks Detected:", self.metric_attacks, _ACCENT_GREEN))
            logs_inner.addLayout(stat_row("Accuracy:", self.metric_accuracy, "#e6a23c"))
            logs_inner.addLayout(stat_row("Top Attacker IP:", self.metric_topip, "#f56c6c"))
            logs_inner.addLayout(stat_row("Attack today:", self.metric_attack_today))
            logs_inner.addLayout(stat_row("Attack (5 min):", self.metric_attack_5m))
            sub_status = QHBoxLayout()
            sub_status.setSpacing(8)
            for t in ("Elasticsearch:", "Filebeat:", "Model:"):
                sub_status.addWidget(QLabel(t))
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
                "Workflow: System Setup → Dataset & Training → Detection Pipeline → Monitoring. "
                "Chọn thao tác ở bảng điều khiển rồi bấm Execute Selected Task. Kết quả hiển thị bên dưới."
            )
            workflow_lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
            workflow_lbl.setWordWrap(True)
            term_inner.addWidget(workflow_lbl)
            timeline_lbl = QLabel("Attacks Timeline (Last 24 Hours)")
            timeline_lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
            term_inner.addWidget(timeline_lbl)
            self.chart_container = QWidget()
            chart_layout = QVBoxLayout(self.chart_container)
            chart_layout.setContentsMargins(0, 0, 0, 0)
            self.chart_placeholder = QLabel("Đang tải…")
            self.chart_placeholder.setMinimumHeight(120)
            self.chart_placeholder.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px; background: {_BG_DARK}; border-radius: 6px;")
            self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(self.chart_placeholder)
            self.chart_view = None
            term_inner.addWidget(self.chart_container)
            self.txt = QPlainTextEdit()
            self.txt.setReadOnly(True)
            self.txt.setPlainText(
                "Chọn thao tác (bấm nút ở 4 cột bên dưới) rồi bấm Thực thi tác vụ đã chọn. Kết quả hiển thị ở đây."
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
            four_cols.addWidget(add_card("⚙", "System Setup", _COLOR_SETUP, [
                ("Reset System", "1. Reset dữ liệu (xóa index)"),
                ("Start Filebeat", "2. Mở Filebeat (cửa sổ mới)"),
                ("Open Kibana", "3. Mở Kibana"),
            ]))
            four_cols.addWidget(add_card("🧠", "Dataset & Training", _COLOR_TRAINING, [
                ("Train Unified Model", "6.1 Train UNIFIED (gộp dataset)"),
                ("Synthetic Dataset", "6.2 Chuẩn bị Synthetic (~8000 dòng)"),
                ("Russell Dataset", "6.3 Train Russell Mitchell"),
                ("Train from CSV", "6.4 Train từ CSV (A/B/C)"),
            ]))
            four_cols.addWidget(add_card("🔍", "Detection Pipeline", _COLOR_DETECTION, [
                ("Run Detection", "7. Detection online (→ ml-alerts)"),
                ("Quick Run", "9. Chạy nhanh: log → pipeline → Kibana"),
                ("Demo Mode", "8. Demo nhanh (chỉ Python)"),
            ]))
            four_cols.addWidget(add_card("📊", "Monitoring", _COLOR_MONITORING, [
                ("Open Kibana Dashboard", "3. Mở Kibana"),
                ("View Alerts", "10. View Alerts"),
                ("System Status", "11. System Status"),
                ("Stack Management", "12. Stack Management"),
            ]))
            main_layout.addLayout(four_cols)

            # 6) Thanh dưới: Execute button (trái) + Log mẫu (phải)
            bottom_bar = QHBoxLayout()
            bottom_bar.setSpacing(12)
            self.btn_run = QPushButton("  ▶  Execute Selected Task  ")
            self.btn_run.setObjectName("runBtn")
            self.btn_run.setFixedHeight(_BTN_HEIGHT)
            self.btn_run.setMinimumWidth(220)
            self.btn_run.clicked.connect(self._on_run_qt)
            bottom_bar.addWidget(self.btn_run)

            self.frame_csv = QWidget()
            csv_layout = QHBoxLayout(self.frame_csv)
            csv_layout.setContentsMargins(0, 0, 0, 0)
            csv_layout.addWidget(QLabel("Tệp CSV:"))
            self.csv_group = QButtonGroup()
            for lab, val in [("A - Russell", "A"), ("B - Kaggle", "B"), ("C - Tệp", "C")]:
                rb = QRadioButton(lab)
                rb.setProperty("value", val)
                if val == "A":
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

            bottom_bar.addStretch()
            log_row = QHBoxLayout()
            log_row.addWidget(QLabel("Log mẫu:"))
            self.spin_normal = QLineEdit()
            self.spin_normal.setFixedWidth(40)
            self.spin_normal.setText("2")
            log_row.addWidget(self.spin_normal)
            log_row.addWidget(QLabel("normal,"))
            self.spin_attack = QLineEdit()
            self.spin_attack.setFixedWidth(40)
            self.spin_attack.setText("5")
            log_row.addWidget(self.spin_attack)
            log_row.addWidget(QLabel("attack"))
            btn_log = QPushButton("Ghi test.log")
            btn_log.setFixedHeight(_BTN_HEIGHT)
            btn_log.setStyleSheet(
                f"QPushButton {{ background-color: {_BORDER}; color: {_TEXT}; border: 1px solid {_TEXT_MUTED}; "
                f"border-radius: {_BTN_RADIUS}px; }} QPushButton:hover {{ background-color: {_TEXT_MUTED}; color: {_BG_DARK}; }}"
            )
            btn_log.clicked.connect(self._on_write_log_qt)
            log_row.addWidget(btn_log)
            log_row.addSpacing(12)
            self.lbl_testlog_status = QLabel("test.log: —")
            self.lbl_testlog_status.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
            log_row.addWidget(self.lbl_testlog_status)
            self.btn_open_testlog = QPushButton("Mở test.log")
            self.btn_open_testlog.setFixedHeight(_BTN_HEIGHT)
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

        def _update_testlog_status_qt(self):
            p = get_testlog_path()
            if p.exists():
                try:
                    size = p.stat().st_size
                    self.lbl_testlog_status.setText(f"test.log: Đã có ({size} bytes)")
                    self.lbl_testlog_status.setToolTip(str(p))
                except Exception:
                    self.lbl_testlog_status.setText("test.log: Đã có")
                    self.lbl_testlog_status.setToolTip(str(p))
            else:
                self.lbl_testlog_status.setText("test.log: Chưa có")
                self.lbl_testlog_status.setToolTip(str(p))

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
            """Khởi chạy lại chương trình (tắt và mở lại) để hiển thị dữ liệu hiện tại."""
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
                self.metric_logs.setText(str(stats.get("logs_count", 0)))
                self.metric_attacks.setText(str(stats.get("attacks_count", 0)))
                acc = stats.get("accuracy")
                self.metric_accuracy.setText(f"{acc}%" if acc is not None else "—")
                if stats.get("top_ip"):
                    c5 = stats.get("top_ip_count_5m") or 0
                    self.metric_topip.setText(f"{stats['top_ip']} ({c5}/5min)" if c5 else stats["top_ip"])
                else:
                    self.metric_topip.setText("—")
                self.metric_attack_today.setText(str(stats.get("attack_today", 0)))
                self.metric_attack_5m.setText(str(stats.get("attack_5min", 0)))
                self.lbl_logs.setText("Log đã xử lý: " + str(stats.get("logs_count", 0)))
                self.lbl_attacks.setText("Tấn công phát hiện: " + str(stats.get("attacks_count", 0)))
                self.lbl_accuracy.setText("Độ chính xác: " + (f"{acc}%" if acc is not None else "—"))
                self.lbl_topip.setText("IP tấn công: " + (stats.get("top_ip") or "—") + "  (5 phút: " + str(stats.get("attack_5min", 0)) + ")")
                hourly = stats.get("hourly_attacks") or [0] * 24
                if HAS_QTCHARTS and self.chart_container:
                    self._build_chart_qt(hourly)
                else:
                    self._build_chart_text_qt(hourly)
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

        def _build_chart_qt(self, hourly):
            try:
                if not HAS_QTCHARTS or not self.chart_container:
                    return
                self._clear_chart_container()
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
                categories = []
                for i in range(24):
                    h = (datetime.now() - timedelta(hours=23 - i)).strftime("%H:%M")
                    categories.append(h)
                axis_x = QBarCategoryAxis()
                axis_x.append(categories)
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                axis_y = QValueAxis()
                axis_y.setRange(0, max(max(hourly, default=0), 1))
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
                chart.legend().setVisible(False)
                chart_view = QChartView(chart)
                chart_view.setMinimumHeight(120)
                chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.chart_container.layout().addWidget(chart_view)
                self.chart_view = chart_view
            except Exception:
                pass

        def _build_chart_text_qt(self, hourly):
            try:
                if not self.chart_container:
                    return
                self._clear_chart_container()
                max_val = max(hourly, default=1) or 1
                blocks = " ▂▃▄▅▆▇█"
                lines = []
                for i in range(0, 24, 2):
                    v = hourly[i] if i < len(hourly) else 0
                    idx = min(int(round(7 * v / max_val)), 7)
                    h = (datetime.now() - timedelta(hours=23 - i)).strftime("%H:%M")
                    lines.append(f"{h} {blocks[idx]}")
                text = "  ".join(lines)
                lbl = QLabel(text)
                lbl.setMinimumHeight(50)
                lbl.setStyleSheet(f"color: {_ACCENT_GREEN}; font-size: 11px; font-family: monospace;")
                self.chart_container.layout().addWidget(lbl)
            except Exception:
                pass

        def _update_status_bar_qt(self):
            try:
                es_ok = check_elasticsearch()
                status = "Đang chạy" if es_ok else "Dừng"
                color = _STATUS_OK if es_ok else _STATUS_FAIL
                self.lbl_es.setText("Elasticsearch: " + status)
                self.lbl_es.setStyleSheet(f"color: {color}; font-size: 10px;")
            except Exception:
                pass
            try:
                loaded = (ROOT / "data" / "models" / "ssh_attack_model.joblib").exists()
                status = "Đã tải" if loaded else "Chưa tải"
                color = _STATUS_OK if loaded else _STATUS_FAIL
                self.lbl_model.setText("Mô hình: " + status)
                self.lbl_model.setStyleSheet(f"color: {color}; font-size: 10px;")
            except Exception:
                pass
            self.lbl_fb.setText("Filebeat: —")
            self.lbl_fb.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")

        def _select_action_qt(self, action_str):
            self.selected_action = action_str
            for a, btn, _ in self.action_buttons:
                btn.setChecked(a == action_str)
            self.frame_csv.setVisible("6.4" in (action_str or ""))
            self.frame_reset_opts.setVisible("1. Reset" in (action_str or ""))

        def _log_qt(self, msg, is_error=False):
            self.msg_queue.put(("log", msg, is_error))

        def _append_log_qt(self, text, is_error):
            self.txt.appendPlainText((text or "") + "\n")
            self.txt.verticalScrollBar().setValue(self.txt.verticalScrollBar().maximum())

        def _process_queue_qt(self):
            try:
                while True:
                    msg = self.msg_queue.get_nowait()
                    if msg[0] == "log":
                        self.log_signal.emit(msg[1] or "", msg[2])
                    elif msg[0] == "done":
                        self.btn_run.setEnabled(True)
            except queue.Empty:
                pass

        def _on_run_qt(self):
            if self.running:
                return
            self.running = True
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
                        self._log_qt("[Xong] Đã gửi lệnh xóa index.")
                    if self.reset_del_processed_cb.isChecked():
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
                    self._log_qt("Bấm Thực thi lần nữa để xác nhận Reset.")

            elif action == "2. Mở Filebeat (cửa sổ mới)":
                fb_dir = ROOT / "config" / "filebeat"
                bat = fb_dir / "Chay_Filebeat.bat"
                if bat.exists():
                    subprocess.Popen(
                        f'start "Filebeat" cmd /k "cd /d "{fb_dir}" && Chay_Filebeat.bat"',
                        shell=True,
                        cwd=str(ROOT),
                    )
                    self._log_qt("Đã mở cửa sổ Filebeat.")
                else:
                    self._log_qt("Không tìm thấy config/filebeat/Chay_Filebeat.bat.", is_error=True)

            elif action == "3. Mở Kibana":
                webbrowser.open("http://localhost:5601")
                ok, out = run_cmd_shell("curl -s http://127.0.0.1:9200/_cat/indices?v 2>nul", timeout=10)
                self._log_qt(out or "Kibana: http://localhost:5601")

            elif action == "6.1 Train UNIFIED (gộp dataset)":
                ok, out = run_cmd(["scripts/train_model.py"], timeout=900)
                self._log_qt(out or "(xong)", is_error=not ok)

            elif action == "6.2 Chuẩn bị Synthetic (~8000 dòng)":
                ok1, out1 = run_cmd(["scripts/generate_synthetic_logs.py", "--total", "8000", "--normal-ratio", "0.85", "--days", "14", "--replace-logs"], timeout=300)
                if ok1:
                    ok2, out2 = run_cmd(["scripts/data_preprocessing.py", "--input", "data/raw/logs.csv", "--output", "data/processed/logs.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack"], timeout=120)
                    self._log_qt(out1 + "\n\n" + out2)
                else:
                    self._log_qt(out1, is_error=True)

            elif action == "6.3 Train Russell Mitchell":
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

            elif action == "6.4 Train từ CSV (A/B/C)":
                rb = self.csv_group.checkedButton()
                val = rb.property("value") if rb else "A"
                custom_path = (self.entry_csv.text() or "").strip()
                write_es = self.write_es_cb.isChecked()
                if val == "A":
                    ok, out = run_cmd(["scripts/data_preprocessing.py", "--input", "data/raw/russellmitchell_auth.csv", "--output", "data/processed/russellmitchell_processed.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack", "--log-type", "ssh"])
                    if ok:
                        ok, out = run_cmd(["scripts/ml_detector.py", "--input", "data/processed/russellmitchell_processed.csv", "--train", "--model-type", "random_forest", "--model-file", "data/models/rf_russellmitchell.joblib", "--output", "data/processed/russellmitchell_predictions.csv", "--handle-imbalance"], timeout=300)
                    if ok and write_es:
                        ok, out = run_cmd(["scripts/elasticsearch_writer.py", "--input", "data/processed/russellmitchell_predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "russellmitchell"])
                    self._log_qt(out or "(xong)", is_error=not ok)
                elif val == "B":
                    if (ROOT / "data" / "ssh_anomaly_dataset.csv").exists():
                        ok, out = run_cmd(["scripts/run_pipeline_ssh.py", "--input", "data/ssh_anomaly_dataset.csv", "--kaggle", "--output-dir", "data", "--model-type", "random_forest"], timeout=600)
                        self._log_qt(out or "(xong)", is_error=not ok)
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
                    self._log_qt("Chọn A/B hoặc nhập đường dẫn CSV hợp lệ (C).", is_error=True)

            elif action == "7. Detection online (→ ml-alerts)":
                if not (ROOT / "data" / "models" / "ssh_attack_model.joblib").exists():
                    self._log_qt("Chưa có model. Chạy [6.1] Train UNIFIED trước.", is_error=True)
                else:
                    ok = run_cmd_stream(["scripts/run_pipeline_detection.py"], str(ROOT), 600, self.msg_queue.put)
                    if not ok:
                        self._log_qt("Detection kết thúc với lỗi hoặc timeout.", is_error=True)

            elif action == "8. Demo nhanh (chỉ Python)":
                ok, out = run_cmd(["scripts/demo_quick.py"], timeout=300)
                self._log_qt(out or "(xong)", is_error=not ok)

            elif action == "9. Chạy nhanh: log → pipeline → Kibana":
                write_sample_log(2, 5)
                self._log_qt("Đã ghi log mẫu. Đợi 15s...")
                import time
                time.sleep(15)
                for step, args in [
                    ("Bước 1", ["scripts/data_extraction.py", "--index", "test-logs-*,ssh-logs-*", "--output", "data/raw/logs.csv", "--hours", "8760", "--host", "127.0.0.1", "--port", "9200"]),
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

            elif action == "10. View Alerts":
                webbrowser.open("http://localhost:5601/app/discover#/?_a=(index:ml-alerts)")
                self._log_qt("Mở Kibana Discover (index ml-alerts).")

            elif action == "11. System Status":
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
                self._log_qt("Đã mở Kibana Stack Management → Index Management.")


if __name__ == "__main__":
    if HAS_QT:
        app = QApplication(sys.argv)
        win = SimulationAppQt()
        win.show()
        sys.exit(app.exec())
    else:
        print("Cần cài PySide6: pip install PySide6")
        sys.exit(1)
