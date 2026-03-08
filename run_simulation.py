#!/usr/bin/env python3
r"""
ELKShield - Chương trình mô phỏng với giao diện đồ họa.

TRÊN WINDOWS: Chạy từ Command Prompt hoặc PowerShell (không dùng nút Run của IDE):
  cd "D:\Do An\Do An An Toan Mang\ELKShield An Intelligent Network Security Monitoring System using Machine Learning"
  python run_simulation.py

Hoặc double-click file: run_simulation.cmd (trong thư mục này).

Script sẽ mở trình duyệt tại http://localhost:8501
"""
import os
import sys
import subprocess
import webbrowser
import html as html_module
from pathlib import Path

# Đảm bảo chạy từ thư mục gốc dự án
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Nếu chạy bằng "python run_simulation.py" (không phải bởi streamlit), tự khởi chạy streamlit
if __name__ == "__main__" and os.environ.get("ELKSHIELD_STREAMLIT") != "1":
    # Kiểm tra đã cài streamlit chưa
    try:
        import streamlit
    except ImportError:
        print("Thieu module Streamlit. Hay cai dat (chay trong cung thu muc du an):")
        print("  py -m pip install streamlit")
        print("Hoac:  python -m pip install streamlit")
        print("Sau do chay lai:  py run_simulation.py   hoac  python run_simulation.py")
        sys.exit(1)
    env = os.environ.copy()
    env["ELKSHIELD_STREAMLIT"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "run_simulation.py"),
         "--server.headless", "true", "--browser.gatherUsageStats", "false"],
        cwd=str(ROOT),
        env=env,
    )
    sys.exit(result.returncode)

import streamlit as st

# --- Cấu hình trang ---
st.set_page_config(
    page_title="ELKShield – Mô phỏng",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS giao diện ---
st.markdown("""
<style>
    /* Header */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1e88e5;
        margin-bottom: 0.25rem;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    .sub-header {
        color: #546e7a;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    /* Cards */
    div[data-testid="stVerticalBlock"] > div {
        border-radius: 12px;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.25rem;
        border: none;
        background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
        color: white;
        transition: box-shadow 0.2s;
    }
    .stButton > button:hover {
        box-shadow: 0 4px 14px rgba(30, 136, 229, 0.45);
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #e6edf3;
    }
    /* Output box */
    .output-box {
        background: #0d1117;
        color: #c9d1d9;
        padding: 1rem;
        border-radius: 8px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 0.85rem;
        max-height: 420px;
        overflow-y: auto;
        border: 1px solid #30363d;
    }
    /* Section titles in sidebar */
    .sidebar-section {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8b949e;
        margin-top: 1rem;
        margin-bottom: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


def run_cmd(args, cwd=None, timeout=600, capture=True):
    """Chạy lệnh Python/script; trả về (success, output_text)."""
    cwd = cwd or str(ROOT)
    try:
        if capture:
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
        else:
            r = subprocess.run(
                [sys.executable] + list(args),
                cwd=cwd,
                timeout=timeout,
            )
            return r.returncode == 0, ""
    except subprocess.TimeoutExpired:
        return False, "[Timeout] Lệnh chạy quá thời gian."
    except Exception as e:
        return False, str(e)


def run_cmd_shell(shell_cmd, cwd=None, timeout=600):
    """Chạy lệnh shell (Windows cmd). Trả về (success, output)."""
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


def write_sample_log(normal: int, attack: int):
    """Ghi file test.log mẫu vào Desktop và Documents."""
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
        except Exception as e:
            pass  # skip if no permission
    return written


def main():
    st.markdown('<p class="main-header">🛡️ ELKShield</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Mô phỏng giám sát an ninh mạng – ELK + ML</p>', unsafe_allow_html=True)

    # --- Sidebar: chọn chức năng ---
    st.sidebar.markdown("### Điều khiển mô phỏng")
    action = st.sidebar.selectbox(
        "Chọn thao tác",
        [
            "— Chọn —",
            "1. Reset dữ liệu (xóa index)",
            "2. Mở Filebeat (cửa sổ mới)",
            "3. Mở Kibana",
            "5. Tạo log mặc định (2 normal + 5 attack)",
            "6.1 Train UNIFIED (gộp dataset)",
            "6.2 Chuẩn bị Synthetic (~8000 dòng)",
            "6.3 Train Russell Mitchell",
            "6.4 Train từ CSV (A/B/C)",
            "7. Detection online (→ ml-alerts)",
            "8. Demo nhanh (chỉ Python)",
            "9. Chạy nhanh: log → pipeline → Kibana",
        ],
        key="action_select",
    )
    run_clicked = st.sidebar.button("▶ Chạy", type="primary")

    # Đảm bảo thư mục
    (ROOT / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "models").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "training").mkdir(parents=True, exist_ok=True)

    output_placeholder = st.empty()
    status_placeholder = st.empty()

    def show_output(msg, is_error=False):
        st.session_state["has_run_output"] = True
        msg_safe = html_module.escape(str(msg)).replace("\n", "<br>")
        output_placeholder.markdown(f'<div class="output-box">{"⚠️ " if is_error else ""}{msg_safe}</div>', unsafe_allow_html=True)

    def run_and_show(args, desc, timeout=600):
        status_placeholder.info(f"⏳ {desc}...")
        ok, out = run_cmd(args, timeout=timeout)
        status_placeholder.empty()
        if ok:
            st.success(f"✅ {desc} – xong.")
        else:
            st.error(f"❌ {desc} – lỗi.")
        show_output(out or "(không có output)", is_error=not ok)
        return ok

    # --- Form cho 6.4 Train CSV (hiện khi chọn 6.4) ---
    csv_choice = None
    custom_path = ""
    write_es_csv = True
    if "6.4" in action:
        st.markdown("#### Tùy chọn Train từ CSV")
        csv_choice = st.radio("Nguồn CSV:", ["A - Russell CSV (data/raw/russellmitchell_auth.csv)", "B - Kaggle SSH (data/ssh_anomaly_dataset.csv)", "C - File bất kỳ"], key="csv_choice", horizontal=True)
        if "C -" in csv_choice:
            custom_path = st.text_input("Đường dẫn file CSV", placeholder="data/raw/my.csv", key="custom_csv_path")
            write_es_csv = st.checkbox("Ghi vào Elasticsearch", value=True, key="write_es_csv")

    # --- Xử lý khi bấm Chạy ---
    if run_clicked and action and action != "— Chọn —":
        if action == "1. Reset dữ liệu (xóa index)":
            if st.session_state.get("confirm_reset", False):
                if (ROOT / "reset_data_silent.bat").exists():
                    ok, out = run_cmd_shell("call reset_data_silent.bat", timeout=60)
                elif (ROOT / "reset_data.bat").exists():
                    ok, out = run_cmd_shell("call reset_data.bat", timeout=60)
                else:
                    out = "Chạy thủ công: curl -X DELETE http://127.0.0.1:9200/test-logs-*\ncurl -X DELETE http://127.0.0.1:9200/ml-alerts-*"
                    ok = True
                show_output(out)
                if "confirm_reset" in st.session_state:
                    del st.session_state["confirm_reset"]
            else:
                st.session_state["confirm_reset"] = True
                st.warning("Bạn có chắc muốn xóa index? Bấm **Chạy** lần nữa để xác nhận.")
                show_output("Chờ xác nhận lần 2.")

        elif action == "2. Mở Filebeat (cửa sổ mới)":
            fb_dir = ROOT / "config" / "filebeat"
            bat = fb_dir / "Chay_Filebeat.bat"
            if bat.exists():
                subprocess.Popen(
                    f'start "Filebeat" cmd /k "cd /d "{fb_dir}" && Chay_Filebeat.bat"',
                    shell=True,
                    cwd=str(ROOT),
                )
                show_output("Đã mở cửa sổ Filebeat. Giữ cửa sổ đó mở; sau đó tạo log [5] → đợi 15s → [7] Detection online.")
            else:
                show_output("Không tìm thấy config/filebeat/Chay_Filebeat.bat.", is_error=True)

        elif action == "3. Mở Kibana":
            webbrowser.open("http://localhost:5601")
            ok, out = run_cmd_shell("curl -s http://127.0.0.1:9200/_cat/indices?v 2>nul", timeout=10)
            show_output(out or "Kibana: http://localhost:5601\nIndex pattern: ml-alerts-*")

        elif action == "5. Tạo log mặc định (2 normal + 5 attack)":
            written = write_sample_log(2, 5)
            if written:
                show_output("Đã ghi 2 normal + 5 attack vào:\n" + "\n".join(written) + "\n\nTiếp: chọn [2] Filebeat (nếu chưa), đợi 15s, rồi [7] Detection online.")
            else:
                show_output("Không ghi được file (kiểm tra quyền Desktop/Documents).", is_error=True)

        elif action == "6.1 Train UNIFIED (gộp dataset)":
            run_and_show(["scripts/train_model.py"], "Train UNIFIED", timeout=900)

        elif action == "6.2 Chuẩn bị Synthetic (~8000 dòng)":
            ok1, out1 = run_cmd(["scripts/generate_synthetic_logs.py", "--total", "8000", "--normal-ratio", "0.85", "--days", "14", "--replace-logs"], timeout=300)
            if ok1:
                ok2, out2 = run_cmd(["scripts/data_preprocessing.py", "--input", "data/raw/logs.csv", "--output", "data/processed/logs.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack"], timeout=120)
                show_output(out1 + "\n\n" + out2)
                st.success("Chuẩn bị Synthetic xong. Tiếp: [6.1] Train UNIFIED hoặc [8] Demo nhanh.")
            else:
                show_output(out1, is_error=True)

        elif action == "6.3 Train Russell Mitchell":
            if not (ROOT / "data" / "russellmitchell" / "gather").exists():
                show_output("Thư mục data/russellmitchell/gather không tồn tại. Đặt dataset Russell Mitchell vào data/russellmitchell.", is_error=True)
            else:
                run_and_show(["scripts/russellmitchell_auth_to_csv.py", "--data-dir", "data/russellmitchell", "--output", "data/raw/russellmitchell_auth.csv", "--with-labels"], "Bước 1/4 Convert auth.log")
                run_and_show(["scripts/data_preprocessing.py", "--input", "data/raw/russellmitchell_auth.csv", "--output", "data/processed/russellmitchell_processed.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack", "--log-type", "ssh"], "Bước 2/4 Preprocess")
                run_and_show(["scripts/ml_detector.py", "--input", "data/processed/russellmitchell_processed.csv", "--train", "--model-type", "random_forest", "--model-file", "data/models/rf_russellmitchell.joblib", "--output", "data/processed/russellmitchell_predictions.csv", "--handle-imbalance"], "Bước 3/4 Train ML", timeout=300)
                run_and_show(["scripts/elasticsearch_writer.py", "--input", "data/processed/russellmitchell_predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "russellmitchell"], "Bước 4/4 Ghi ES")

        elif action == "6.4 Train từ CSV (A/B/C)":
            if csv_choice is None:
                csv_choice = "A - Russell CSV (data/raw/russellmitchell_auth.csv)"
            if "A -" in csv_choice:
                run_and_show(["scripts/data_preprocessing.py", "--input", "data/raw/russellmitchell_auth.csv", "--output", "data/processed/russellmitchell_processed.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack", "--log-type", "ssh"], "Preprocess Russell")
                run_and_show(["scripts/ml_detector.py", "--input", "data/processed/russellmitchell_processed.csv", "--train", "--model-type", "random_forest", "--model-file", "data/models/rf_russellmitchell.joblib", "--output", "data/processed/russellmitchell_predictions.csv", "--handle-imbalance"], "Train Russell", timeout=300)
                run_and_show(["scripts/elasticsearch_writer.py", "--input", "data/processed/russellmitchell_predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "russellmitchell"], "Ghi ES")
            elif "B -" in csv_choice:
                if (ROOT / "data" / "ssh_anomaly_dataset.csv").exists():
                    run_and_show(["scripts/run_pipeline_ssh.py", "--input", "data/ssh_anomaly_dataset.csv", "--kaggle", "--output-dir", "data", "--model-type", "random_forest"], "Pipeline Kaggle SSH", timeout=600)
                else:
                    show_output("Chưa có file data/ssh_anomaly_dataset.csv. Đặt file vào thư mục data/.", is_error=True)
            elif "C -" in csv_choice and custom_path and (ROOT / custom_path.strip()).exists():
                cp = custom_path.strip()
                run_and_show(["scripts/data_preprocessing.py", "--input", cp, "--output", "data/processed/custom_processed.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack", "--log-type", "ssh"], "Preprocess")
                run_and_show(["scripts/ml_detector.py", "--input", "data/processed/custom_processed.csv", "--train", "--model-type", "random_forest", "--model-file", "data/models/rf_custom.joblib", "--output", "data/processed/custom_predictions.csv", "--handle-imbalance"], "Train", timeout=300)
                if write_es_csv:
                    run_and_show(["scripts/elasticsearch_writer.py", "--input", "data/processed/custom_predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "csv"], "Ghi ES")
            else:
                show_output("Chọn A/B hoặc nhập đường dẫn file CSV hợp lệ (C).", is_error=True)

        elif action == "7. Detection online (→ ml-alerts)":
            if not (ROOT / "data" / "models" / "ssh_attack_model.joblib").exists():
                show_output("Chưa có model unified. Chạy [6.1] Train UNIFIED trước. Hoặc bật [2] Filebeat nếu cần log từ ES.", is_error=True)
            else:
                run_and_show(["scripts/run_pipeline_detection.py"], "Detection online", timeout=600)

        elif action == "8. Demo nhanh (chỉ Python)":
            run_and_show(["scripts/demo_quick.py"], "Demo nhanh", timeout=300)

        elif action == "9. Chạy nhanh: log → pipeline → Kibana":
            write_sample_log(2, 5)
            status_placeholder.info("Đã ghi log mẫu. Đợi 15s để Filebeat gửi lên ES...")
            import time
            time.sleep(15)
            run_and_show(["scripts/data_extraction.py", "--index", "test-logs-*,ssh-logs-*", "--output", "data/raw/logs.csv", "--hours", "8760", "--host", "127.0.0.1", "--port", "9200"], "Bước 1 Extract")
            run_and_show(["scripts/data_preprocessing.py", "--input", "data/raw/logs.csv", "--output", "data/processed/logs.csv", "--clean", "--extract-time", "--extract-ip", "--extract-attack"], "Bước 2 Preprocess")
            run_and_show(["scripts/ml_detector.py", "--input", "data/processed/logs.csv", "--train", "--model-type", "isolation_forest", "--model-file", "data/models/rf_ssh_isolation_forest.joblib", "--output", "data/predictions.csv"], "Bước 3 ML", timeout=300)
            run_and_show(["scripts/elasticsearch_writer.py", "--input", "data/predictions.csv", "--index", "ml-alerts", "--host", "127.0.0.1", "--port", "9200", "--model-name", "synthetic"], "Bước 4 Ghi ES")
            webbrowser.open("http://localhost:5601")
            st.success("Chạy nhanh xong. Kibana đã mở – xem index pattern ml-alerts-*.")

    # --- Gợi ý thứ tự ---
    st.sidebar.markdown("---")
    st.sidebar.caption("Thứ tự gợi ý: [5] tạo log → [2] Filebeat → [6.1] Train unified → [7] Detection → [3] Kibana")

    # Hiển thị output mặc định chỉ lần đầu (chưa chạy lệnh nào)
    if not st.session_state.get("has_run_output"):
        output_placeholder.markdown(
            '<div class="output-box">Chọn thao tác bên trái và bấm <b>▶ Chạy</b> để mô phỏng.<br><br>'
            'Thứ tự gợi ý: Tạo log [5] → Filebeat [2] → Train UNIFIED [6.1] → Detection [7] → Kibana [3].</div>',
            unsafe_allow_html=True,
        )

    # Form tạo log tùy chỉnh (số dòng)
    with st.expander("📝 Tạo log mẫu (tùy chỉnh số dòng)"):
        c1, c2 = st.columns(2)
        with c1:
            n_normal = st.number_input("Số dòng bình thường", min_value=0, value=2, step=1)
        with c2:
            n_attack = st.number_input("Số dòng tấn công", min_value=0, value=5, step=1)
        if st.button("Ghi file test.log"):
            written = write_sample_log(int(n_normal), int(n_attack))
            if written:
                st.success(f"Đã ghi {n_normal + n_attack} dòng vào " + ", ".join(written))
            else:
                st.error("Không ghi được file.")


if __name__ == "__main__":
    # Chỉ gọi main() khi đang chạy bởi Streamlit (đã set ELKSHIELD_STREAMLIT=1)
    if os.environ.get("ELKSHIELD_STREAMLIT") == "1":
        main()
