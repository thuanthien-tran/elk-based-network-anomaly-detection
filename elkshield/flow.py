"""
Unified pipeline: Check ELK → Load Model → Collect Logs → Feature Extraction → ML Detection → Write Alert ES → Suggest Defense → Dashboard Update.
Research architecture — one orchestrator.
"""
from pathlib import Path

from elkshield.core import collector, processor, ml_engine, defense
from elkshield.siem import elastic, kibana

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "raw" / "logs.csv"
PROCESSED_CSV = ROOT / "data" / "processed" / "logs.csv"
PREDICTIONS_CSV = ROOT / "data" / "predictions.csv"


def _log(cb, msg, is_error=False):
    if cb:
        try:
            cb("log", msg, is_error)
        except Exception:
            pass


def run_monitoring_flow(log_callback=None, open_browser=True, write_test_log_first=True):
    """
    Run full monitoring flow (research architecture).
    log_callback(msg_type, text, is_error) — e.g. queue.put for GUI.
    Returns (success: bool, message: str).
    """
    def log(msg, err=False):
        _log(log_callback, msg, err)

    log("=== ELKShield Unified Security Platform — Start Monitoring ===")

    # 1. Check ELK
    log("1. Check ELK...")
    if not elastic.check_elasticsearch():
        log("Elasticsearch không chạy. Detection sẽ dùng fallback test.log.", err=True)
    else:
        log("   Elasticsearch: OK")

    # 2. Load Model
    log("2. Load Model...")
    model_path = ml_engine.load_model()
    if not model_path:
        log("Chưa có model. Chạy Train UNIFIED trước (Dataset & Training).", err=True)
        return False, "No model"
    log("   Model: %s" % Path(model_path).name)

    # 3. Collect Logs (optional: write test.log to simulate attack)
    if write_test_log_first:
        log("3. Collect Logs (tạo test.log mô phỏng tấn công)...")
        written = collector.write_test_log(3, 5)
        if written:
            log("   Đã ghi: %s" % written[0])
        else:
            log("   Không ghi được test.log.", err=True)
    else:
        log("3. Collect Logs...")

    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)

    ok_es, _, _ = collector.collect_logs_from_es(output_csv=str(RAW_CSV))
    if not ok_es:
        log("   Fallback: đọc từ test.log")
        ok_file, _, _ = collector.collect_logs_from_file(output_csv=str(RAW_CSV))
        if not ok_file:
            log("   Không lấy được log. Kiểm tra test.log hoặc Filebeat.", err=True)
            return False, "No logs"
    else:
        log("   Đã lấy log từ Elasticsearch")

    # 4. Feature Extraction (preprocessing)
    log("4. Feature Extraction...")
    ok_pre, out_pre, _ = processor.run_preprocessing(
        str(RAW_CSV), str(PROCESSED_CSV), log_type="ssh", timeout=120
    )
    if not ok_pre:
        log("   Preprocess thất bại: %s" % (out_pre or "lỗi"), err=True)
        return False, "Preprocess failed"
    log("   OK")

    # 5. ML Detection
    log("5. ML Detection...")
    ok_pred, out_pred, pred_path = ml_engine.predict(
        str(PROCESSED_CSV), output_csv=str(PREDICTIONS_CSV), timeout=300
    )
    if not ok_pred:
        log("   Prediction thất bại.", err=True)
        return False, "Predict failed"
    log("   OK -> %s" % pred_path)

    # 6. Write Alert ES (SIEM Integration)
    log("6. Write Alert ES (Suggest Defense gắn trong bản ghi)...")
    ok_es_write, out_es = elastic.write_alerts_to_es(
        pred_path, index_name="ml-alerts", model_name="unified", timeout=300
    )
    if not ok_es_write:
        log("   Ghi ES cảnh báo: lỗi (kết quả vẫn lưu file).", err=True)
        if out_es and out_es.strip():
            for line in out_es.strip().splitlines()[:15]:
                log("   %s" % line, err=True)
    else:
        log("   OK -> ml-alerts-*")

    # 7. Suggest Defense (Defense Engine — SOAR)
    log("7. Suggest Defense (rule engine đã gắn trong ml-alerts)...")
    log("   Xem đề xuất: nút 'Xem đề xuất phòng thủ' hoặc trường defense_recommendations trên Kibana.")

    # 8. Dashboard Update
    log("8. Dashboard Update...")
    if open_browser:
        kibana.open_discover_alerts("ml-alerts")
        log("   Đã mở Kibana Discover (ml-alerts).")
    log("=== Start Monitoring hoàn tất ===")
    return True, "OK"


if __name__ == "__main__":
    run_monitoring_flow(log_callback=lambda t, msg, err: print(msg), open_browser=True)
