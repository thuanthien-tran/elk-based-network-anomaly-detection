# ELKShield – Intelligent Network Security Monitoring (ELK + ML)

Hệ thống giám sát an ninh mạng dựa trên ELK Stack và Machine Learning (SSH/web logs, anomaly detection).

## Hướng dẫn nhanh

- **Hướng dẫn thực hiện & chạy demo:** [HUONG_DAN_THUC_HIEN_DU_AN.md](HUONG_DAN_THUC_HIEN_DU_AN.md)
- **Chạy từng bước:** [HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md)
- **Dataset thật & pipeline mới:** [HUONG_DAN_DATASET_THAT_VA_PIPELINE.md](HUONG_DAN_DATASET_THAT_VA_PIPELINE.md)
- **Demo:** thư mục [Demo/](Demo/) – chạy **DEMO.bat**; [6] Chọn dataset để train (gồm [5] Train unified model); [1] Detection online dùng model đã train.
- **Mô phỏng (giao diện):** Chạy **`python run_simulation.py`** – mở giao diện web (Streamlit) tại http://localhost:8501 để chọn và chạy từng bước (Reset, Filebeat, Kibana, tạo log, Train, Detection, Demo). Cần cài: `pip install streamlit`.
- **Ứng dụng desktop (không dùng web):** Chạy **`python run_simulation_app.py`** – mở cửa sổ ứng dụng (CustomTkinter), cùng chức năng mô phỏng. Cần cài: `pip install customtkinter`. Nếu chưa cài CustomTkinter, chương trình vẫn chạy được với giao diện tkinter mặc định.

## Thành phần chính

- **scripts/** – Python: trích xuất log (data_extraction), tiền xử lý (data_preprocessing), ML (ml_detector), ghi ES (elasticsearch_writer), **analyze_datasets** (phân tích dataset), **run_pipeline_ssh** (chạy pipeline SSH một lệnh)
- **data/** – Dataset (raw, processed, models), xem [data/README.md](data/README.md)
- **config/** – Filebeat, Logstash pipeline
- **docker/** – docker-compose cho ELK

## Cải tiến gần đây

- **Kiến trúc SIEM + ML Hybrid (research-style):** Offline training (gộp 3 dataset → train RF → `ssh_attack_model.joblib`) + Online detection (ELK logs → model → ml-alerts → Kibana). Chi tiết và **checklist task hoàn thành:** [docs/TASK_HOAN_THANH_SIEM_ML.md](docs/TASK_HOAN_THANH_SIEM_ML.md).
- **Dataset cải tiến:** Script `scripts/generate_synthetic_logs.py` sinh SSH log đa dạng (nhiều ngày/giờ, nhiều IP/user tấn công, normal: password/publickey/session, ít “failed rồi accepted”). DEMO.bat **[13] Tao dataset cai tien** chạy sinh → ghi đè `data/raw/logs.csv` → preprocess → `data/processed/logs.csv`. Lệnh tay: `python scripts/generate_synthetic_logs.py --total 8000 --normal-ratio 0.85 --days 14 [--replace-logs]`.
- **ML:** `ml_detector.py` hỗ trợ `--tune` (GridSearchCV cho Random Forest), `--metrics-output` (lưu precision/recall/F1/ROC-AUC ra JSON).
- **Phân tích:** `python scripts/analyze_datasets.py --data-dir data [--csv-detail]` để liệt kê và thống kê dataset.
- **Pipeline một lệnh:** `python scripts/run_pipeline_ssh.py --input data/ssh_anomaly_dataset.csv --kaggle --output-dir data` (convert → preprocess → train → lưu model + metrics).
- **API inference real-time:** `python scripts/inference_api.py --model-file data/models/rf_ssh_random_forest.joblib --port 5000` → POST /predict với JSON records.
- **Pipeline web:** `python scripts/run_pipeline_web.py --input data/apache-http-logs-master/acunetix.txt --from-apache --output-dir data`.
- **Dataset Russell Mitchell:** auth.log trong `data/russellmitchell/gather/*/logs/` → `python scripts/russellmitchell_auth_to_csv.py --data-dir data/russellmitchell --output data/raw/russellmitchell_auth.csv [--with-labels]` rồi chạy pipeline SSH với file CSV đó. Xem [data/russellmitchell/README.md](data/russellmitchell/README.md).
- **Bảo mật ELK:** Xem [docs/BAO_MAT_ELK.md](docs/BAO_MAT_ELK.md) (lab vs production, xpack, user/password, TLS).
- **Kiểm thử:** `pip install -r requirements-dev.txt` rồi `pytest tests/`. CI: GitHub Actions chạy pytest trên push/PR (xem [.github/workflows/test.yml](.github/workflows/test.yml)).
- **Inference API** cần Flask: `pip install flask`. Bảo mật: `--api-key` hoặc `--basic-auth user:pass` (hoặc env `ELKSHIELD_API_KEY`).
- **Dashboard & Cảnh báo Kibana:** [docs/HUONG_DAN_DASHBOARD_KIBANA.md](docs/HUONG_DAN_DASHBOARD_KIBANA.md), [docs/HUONG_DAN_ALERTING_KIBANA.md](docs/HUONG_DAN_ALERTING_KIBANA.md).
- **Xử lý lỗi thường gặp:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).
- **Pipeline web (train + ml-alerts):** `run_pipeline_web.py --input ... [--from-apache] --train --write-es` → ghi ml-alerts với `ml_model=web`.
- **Near real-time detection:** Chạy detection theo chu kỳ (cron/Task Scheduler): [docs/NEAR_REALTIME_DETECTION.md](docs/NEAR_REALTIME_DETECTION.md); dùng `run_detection_interval.bat` / `run_detection_interval.sh`.

## Chạy production

Cấu hình mặc định (HTTP, không xác thực) phù hợp **lab/demo**. Khi triển khai thật (máy chạy 24/7, nhiều người dùng, expose internet):

- **Bảo mật ELK:** Bật xpack security, user/password, TLS cho Elasticsearch và Kibana; cấu hình Filebeat, Logstash và script Python dùng credentials. Chi tiết từng bước: **[docs/BAO_MAT_ELK.md](docs/BAO_MAT_ELK.md)**.
- **API inference:** Chạy với `--api-key` hoặc `--basic-auth`; không bind `0.0.0.0` nếu không cần truy cập từ ngoài.
- **Kibana:** Tạo rule cảnh báo (Alerting) và dashboard theo [docs/HUONG_DAN_ALERTING_KIBANA.md](docs/HUONG_DAN_ALERTING_KIBANA.md), [docs/HUONG_DAN_DASHBOARD_KIBANA.md](docs/HUONG_DAN_DASHBOARD_KIBANA.md).

## Yêu cầu tài nguyên (gợi ý)

- **RAM:** Tối thiểu 4 GB cho máy chạy Docker (ELK) + Python; dataset > 100k dòng nên 8 GB; train unified lớn hoặc extract ES nhiều batch nên 8–16 GB.
- **Ổ đĩa:** ~2 GB cho Docker images; thêm dung lượng theo size dataset (raw/processed) và index Elasticsearch (ml-alerts-*, test-logs-* tăng theo thời gian).
- **Elasticsearch:** Mặc định heap ~1 GB; có thể tăng trong docker-compose nếu index lớn.
- **Encoding:** File log nên UTF-8; nếu log Windows/ISO-8859, dùng `--encoding` (ví dụ `apache_log_to_csv.py --encoding utf-8` hoặc cp1252 khi cần).
