# Mô tả từng chức năng – Ứng dụng ELKShield (run_simulation_app.py)

Ứng dụng desktop gồm 4 nhóm chức năng (4 cột nút) và một số nút/panel phụ. Chọn một thao tác rồi bấm **Execute Selected Task** để thực thi.

---

## 1. System Setup (Thiết lập hệ thống)

| Chức năng | Mô tả |
|-----------|--------|
| **Reset System** | Xóa index Elasticsearch: `test-logs-*` và `ml-alerts-*`. Có thể gọi thêm `reset_data_silent.bat` / `reset_data.bat` nếu có. **Cần bấm Execute 2 lần** để xác nhận. Khi chọn Reset, thanh dưới hiện 2 tùy chọn: **Xóa cả model khi Reset** (xóa toàn bộ file `.joblib` trong `data/models/`) và **Xóa cả dữ liệu đã xử lý** (xóa `logs.csv`, các file `*_predictions.csv`, `predictions.csv`). |
| **Start Filebeat** | Mở cửa sổ CMD mới và chạy `config/filebeat/Chay_Filebeat.bat` để khởi động Filebeat thu thập log (đọc file log → gửi Logstash/Elasticsearch). Cần có sẵn file batch và cấu hình Filebeat. |
| **Open Kibana** | Mở trình duyệt tại `http://localhost:5601` và in ra danh sách index ES (qua curl) để kiểm tra nhanh. |

---

## 2. Dataset & Training (Dữ liệu & Huấn luyện)

| Chức năng | Mô tả |
|-----------|--------|
| **Train UNIFIED (gộp 3 dataset → model chính)** | Chạy `scripts/train_model.py`: gộp 3 nguồn (Synthetic + Russell Mitchell + Kaggle) thành `data/training/unified_ssh_dataset.csv`, làm sạch, train Random Forest và lưu **`data/models/ssh_attack_model.joblib`**. Đây là model dùng cho **Detection online (mục 7)**. Cần đã có dữ liệu từ Synthetic, Russell và/hoặc Kaggle (đã preprocess). |
| **Chuẩn bị & Train (Synthetic / Russell)** | Một mục với **2 lựa chọn** ở thanh dưới (Nguồn: **Synthetic** hoặc **Russell Mitchell**). **Synthetic:** Chạy `generate_synthetic_logs.py` tạo ~8000 dòng log SSH → ghi `data/raw/logs.csv` → preprocess → `data/processed/logs.csv`. **Russell Mitchell:** (1) Convert auth.log trong `data/russellmitchell/gather` sang CSV, (2) preprocess, (3) train RF → `rf_russellmitchell.joblib` và `russellmitchell_predictions.csv`, (4) ghi kết quả lên Elasticsearch (index ml-alerts, model-name russellmitchell). Cần có thư mục `data/russellmitchell/gather`. |
| **Train từ CSV (Kaggle / tệp)** | Train từ file CSV có sẵn. Thanh dưới có 2 lựa chọn: **Kaggle (ssh_anomaly_dataset):** Chạy `run_pipeline_ssh.py` với `data/ssh_anomaly_dataset.csv` (định dạng Kaggle), convert → preprocess → train → lưu model trong `data/models/`. **Tệp (đường dẫn):** Nhập đường dẫn CSV (vd. `data/raw/my.csv`) → preprocess → train → `rf_custom.joblib` và `custom_predictions.csv`; nếu bật **Ghi ES** thì ghi cảnh báo lên ml-alerts (model-name csv). |

---

## 3. Detection Pipeline (Luồng phát hiện)

| Chức năng | Mô tả |
|-----------|--------|
| **Run Detection** | Chạy `scripts/run_pipeline_detection.py`: lấy log từ Elasticsearch (hoặc fallback từ `test.log`) → preprocess → load **`ssh_attack_model.joblib`** → dự đoán → ghi kết quả vào index **ml-alerts** (model-name unified). **Điều kiện:** Đã chạy **Train UNIFIED (6.1)** để có file `ssh_attack_model.joblib`. Output hiển thị theo dòng trong Terminal Output. |

---

## 4. Monitoring (Giám sát)

| Chức năng | Mô tả |
|-----------|--------|
| **Open Kibana Dashboard** | Giống **3. Mở Kibana**: mở Kibana tại `http://localhost:5601`. |
| **View Alerts** | Mở Kibana Discover với index **ml-alerts** sẵn chọn, để xem cảnh báo ML đã ghi. |
| **System Status** | In ra trạng thái: Elasticsearch (Đang chạy/Dừng), Kibana, file model `ssh_attack_model.joblib`, file `test.log`, cấu hình Filebeat, `data/processed/logs.csv`, thư mục `data/raw`, danh sách file model trong `data/models`, và (nếu ES chạy) danh sách index. |
| **Stack Management** | Mở Kibana → Stack Management → Index Management (quản lý index Elasticsearch). |

---

## 5. Các chức năng khác (trong menu / panel)

Các thao tác sau có trong logic nhưng **không nằm trong 4 cột nút** (có thể gọi từ menu hoặc shortcut tùy phiên bản):

| Chức năng | Mô tả |
|-----------|--------|
| **8. Demo nhanh (chỉ Python)** | Chạy `scripts/demo_quick.py` – demo nhanh bằng Python (không qua ELK). |
| **9. Chạy nhanh: log → pipeline → Kibana** | Ghi log mẫu (2 normal, 5 attack) vào test.log → đợi 15s → extract từ ES → preprocess → train Isolation Forest → ghi predictions lên ml-alerts → mở Kibana. Dùng để demo nhanh toàn luồng. |

---

## 6. Nút và panel phụ

| Thành phần | Mô tả |
|------------|--------|
| **Execute Selected Task** | Thực thi thao tác đã chọn (một trong các action ở 4 cột). |
| **Làm mới** | Cập nhật lại thống kê (số log, số tấn công, độ chính xác, IP tấn công, Attacks Timeline) và trạng thái Elasticsearch / Model. Dữ liệu đọc từ `data/processed/logs.csv` và các file predictions. |
| **Ghi log** | Mở panel nhập số dòng log “normal” và “attack”, rồi ghi vào file test.log (mặc định trong thư mục Documents). Dùng để tạo dữ liệu mẫu cho Filebeat/Detection. |
| **Reset (trong panel)** | Khi chọn **1. Reset dữ liệu**, thanh dưới hiện 2 checkbox: **Xóa cả model khi Reset** và **Xóa cả dữ liệu đã xử lý (logs.csv, predictions)**. |
| **Thanh trạng thái (status bar)** | Hiển thị Elasticsearch (Đang chạy/Dừng), Model (Đã tải/Chưa tải), Filebeat (—). |
| **Terminal Output** | Vùng hiển thị log kết quả khi chạy các lệnh (Reset, Train, Detection, Status, v.v.). |
| **Attacks Timeline (Last 24 Hours)** | Biểu đồ cột (hoặc text) số tấn công theo từng giờ trong 24h qua; dữ liệu lấy từ `data/processed/logs.csv` và các file predictions. |

---

## 7. Luồng đề xuất (demo / đồ án)

1. **System Setup:** Bật Elasticsearch (Docker), Kibana. Có thể bật Filebeat nếu dùng log từ file.
2. **Dataset & Training:** Chạy **Chuẩn bị & Train** → chọn Synthetic (hoặc Russell nếu có dữ liệu) → sau đó chạy **Train UNIFIED** để tạo `ssh_attack_model.joblib`.
3. **Detection:** Chạy **Run Detection** để đọc log (từ ES hoặc test.log) → predict → ghi ml-alerts.
4. **Monitoring:** Bấm **View Alerts** để xem cảnh báo trên Kibana; dùng **Làm mới** để cập nhật thống kê và timeline.
