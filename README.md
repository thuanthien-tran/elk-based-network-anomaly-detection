# ELKShield – Intelligent Network Security Monitoring (ELK + ML)

Hệ thống giám sát an ninh mạng dựa trên ELK Stack và Machine Learning (SSH/web logs, anomaly detection).

## Chạy thống nhất (Unified Security Platform)

- **Một chương trình điều phối:** `python elkshield.py` — mở dashboard (PySide6). Bấm **▶ Start Monitoring** → hệ thống chạy: Check ELK → Load Model → Collect Logs → Feature Extraction → ML Detection → Write Alert ES → Suggest Defense → mở Kibana. Đây là kiến trúc research (Core + SIEM + UI).
- **CLI:** `python elkshield.py --monitor` (chạy flow đầy đủ), `python elkshield.py --train` (train UNIFIED), `python elkshield.py --gui` (mở dashboard).
- **Cấu trúc package:** `elkshield/core/` (collector, processor, ml_engine, defense), `elkshield/siem/` (elastic, kibana), `elkshield/ui/` (dashboard, cli), `elkshield/flow.py` (luồng Start Monitoring).

## Hướng dẫn nhanh (script rời)

- **Hướng dẫn thực hiện & chạy demo:** [HUONG_DAN_THUC_HIEN_DU_AN.md](HUONG_DAN_THUC_HIEN_DU_AN.md)
- **Chạy từng bước:** [HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md)
- **Dataset thật & pipeline mới:** [HUONG_DAN_DATASET_THAT_VA_PIPELINE.md](HUONG_DAN_DATASET_THAT_VA_PIPELINE.md)
- **Demo:** thư mục [Demo/](Demo/) – chạy **DEMO.bat**; [6] Chọn dataset để train (gồm [5] Train unified model); [1] Detection online dùng model đã train.
- **Ứng dụng desktop (tương đương elkshield.py):** **`python run_simulation_app.py`** – cùng dashboard với **Start Monitoring**. Cần cài: `pip install PySide6`.

## Kiến trúc (Research Paper)

ELKShield theo kiến trúc 5 tầng: **Data Layer** (Heterogeneous Log Sources) → **SIEM Layer** (ELK: ingestion, parsing, correlation, storage, visualization) → **ML Layer** (AI-Driven Threat Detection: offline train + online detection) → **Hybrid Detection** (rule-based + ML) → **Response Layer** (Semi-Automated: alert, visualization, suggest defense; future: auto block, firewall/IDS). Chi tiết và sơ đồ: **[docs/ARCHITECTURE_RESEARCH.md](docs/ARCHITECTURE_RESEARCH.md)**.

## Thành phần chính

- **scripts/** – Python: trích xuất log (data_extraction), tiền xử lý (data_preprocessing), ML (ml_detector), ghi ES (elasticsearch_writer), **analyze_datasets** (phân tích dataset), **run_pipeline_ssh** (chạy pipeline SSH một lệnh)
- **data/** – Dataset (raw, processed, models), xem [data/README.md](data/README.md)
- **config/** – Filebeat, Logstash pipeline (rule-based: brute force, SQLi, XSS)
- **docker/** – docker-compose cho ELK

## Cải tiến gần đây

- **Kiến trúc SIEM + ML Hybrid (research-style):** Offline training (gộp 3 dataset → train RF → `ssh_attack_model.joblib`) + Online detection (ELK logs → model → ml-alerts → Kibana). Chi tiết và **checklist task hoàn thành:** [docs/TASK_HOAN_THANH_SIEM_ML.md](docs/TASK_HOAN_THANH_SIEM_ML.md).
- **Dataset cải tiến:** Script `scripts/generate_synthetic_logs.py` sinh SSH log đa dạng (nhiều ngày/giờ, nhiều IP/user tấn công, normal: password/publickey/session, ít “failed rồi accepted”). DEMO.bat **[13] Tao dataset cai tien** chạy sinh → ghi đè `data/raw/logs.csv` → preprocess → `data/processed/logs.csv`. Lệnh tay: `python scripts/generate_synthetic_logs.py --total 8000 --normal-ratio 0.85 --days 14 [--replace-logs]`.
- **ML:** `ml_detector.py` hỗ trợ `--tune` (GridSearchCV cho Random Forest), `--metrics-output` (lưu precision/recall/F1/ROC-AUC ra JSON).
- **Phân tích:** `python scripts/analyze_datasets.py --data-dir data [--csv-detail]` để liệt kê và thống kê dataset.
- **Pipeline một lệnh:** `python scripts/run_pipeline_ssh.py --input data/ssh_anomaly_dataset.csv --kaggle --output-dir data` (convert → preprocess → train → lưu model + metrics).
- **Dataset Russell Mitchell:** auth.log trong `data/russellmitchell/gather/*/logs/` → `python scripts/russellmitchell_auth_to_csv.py --data-dir data/russellmitchell --output data/raw/russellmitchell_auth.csv [--with-labels]` rồi chạy pipeline SSH với file CSV đó. Xem [data/russellmitchell/README.md](data/russellmitchell/README.md).
- **Bảo mật ELK:** Xem [docs/BAO_MAT_ELK.md](docs/BAO_MAT_ELK.md) (lab vs production, xpack, user/password, TLS).
- **Kiểm thử:** `pip install -r requirements-dev.txt` rồi `pytest tests/`. CI: GitHub Actions chạy pytest trên push/PR (xem [.github/workflows/test.yml](.github/workflows/test.yml)).
- **Dashboard & Cảnh báo Kibana:** [docs/HUONG_DAN_DASHBOARD_KIBANA.md](docs/HUONG_DAN_DASHBOARD_KIBANA.md), [docs/HUONG_DAN_ALERTING_KIBANA.md](docs/HUONG_DAN_ALERTING_KIBANA.md).
- **Xử lý lỗi thường gặp:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).
- **Near real-time detection:** Chạy detection theo chu kỳ (cron/Task Scheduler): [docs/NEAR_REALTIME_DETECTION.md](docs/NEAR_REALTIME_DETECTION.md).

## Chạy production

Cấu hình mặc định (HTTP, không xác thực) phù hợp **lab/demo**. Khi triển khai thật (máy chạy 24/7, nhiều người dùng, expose internet):

- **Bảo mật ELK:** Bật xpack security, user/password, TLS cho Elasticsearch và Kibana; cấu hình Filebeat, Logstash và script Python dùng credentials. Chi tiết từng bước: **[docs/BAO_MAT_ELK.md](docs/BAO_MAT_ELK.md)**.
- **Kibana:** Tạo rule cảnh báo (Alerting) và dashboard theo [docs/HUONG_DAN_ALERTING_KIBANA.md](docs/HUONG_DAN_ALERTING_KIBANA.md), [docs/HUONG_DAN_DASHBOARD_KIBANA.md](docs/HUONG_DAN_DASHBOARD_KIBANA.md).

## Yêu cầu tài nguyên (gợi ý)

- **RAM:** Tối thiểu 4 GB cho máy chạy Docker (ELK) + Python; dataset > 100k dòng nên 8 GB; train unified lớn hoặc extract ES nhiều batch nên 8–16 GB.
- **Ổ đĩa:** ~2 GB cho Docker images; thêm dung lượng theo size dataset (raw/processed) và index Elasticsearch (ml-alerts-*, test-logs-* tăng theo thời gian).
- **Elasticsearch:** Mặc định heap ~1 GB; có thể tăng trong docker-compose nếu index lớn.
- **Encoding:** File log nên UTF-8; nếu log Windows/ISO-8859, dùng tham số `--encoding` tương ứng (vd. cp1252) trong script xử lý.
