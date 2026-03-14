# Dàn ý báo cáo đồ án – ELKShield

Tài liệu này gợi ý cấu trúc báo cáo đồ án (văn bản / slide thuyết trình) dựa trên dự án ELKShield. Có thể copy nội dung từ các file trong repo vào từng mục.

---

## 1. Mở đầu

- **Tên đề tài:** ELKShield – An Intelligent Network Security Monitoring System using Machine Learning
- **Mục tiêu:** Xây dựng hệ thống giám sát an ninh mạng kết hợp ELK Stack và Machine Learning để phát hiện bất thường (anomaly) trên log SSH (và web).
- **Phạm vi:** Thu thập log → parse → trích đặc trưng → huấn luyện mô hình (offline) → phát hiện (online) → ghi cảnh báo lên Elasticsearch/Kibana.

**Nguồn tham khảo trong repo:**  
- [README.md](../README.md) – tổng quan, thành phần chính  
- [DANH_GIA_DU_AN_ELKShield.md](../DANH_GIA_DU_AN_ELKShield.md) – đánh giá điểm mạnh/yếu, chấm điểm

---

## 2. Cơ sở lý thuyết / Công nghệ sử dụng

- **ELK Stack:** Elasticsearch (lưu trữ, tìm kiếm), Logstash (parse log, Grok), Kibana (trực quan hóa), Filebeat (thu thập log).
- **Machine Learning:** Random Forest (supervised), Isolation Forest / One-Class SVM (unsupervised); tiền xử lý (đặc trưng SSH: failed login, time window, IP; web: status code, 4xx/5xx, error rate).
- **Kiến trúc hybrid:** Huấn luyện offline từ nhiều dataset → lưu model → phát hiện online từ log ELK, ghi kết quả vào index `ml-alerts-*`.

**Nguồn tham khảo:**  
- [docs/TASK_HOAN_THANH_SIEM_ML.md](TASK_HOAN_THANH_SIEM_ML.md) – phương án SIEM + ML, luồng offline/online

---

## 3. Kiến trúc hệ thống

- **Sơ đồ tổng thể:**  
  - **Offline:** Gộp dataset (Synthetic + Russell Mitchell + Kaggle) → tiền xử lý → train Random Forest → `ssh_attack_model.joblib`.  
  - **Online:** Log (file/ES) → Filebeat → Logstash → Elasticsearch → trích xuất → tiền xử lý → load model → dự đoán → ghi `ml-alerts-*` → Kibana.

- **Thành phần chính:**  
  - `scripts/`: merge_training_datasets, train_model, run_pipeline_detection, data_preprocessing, ml_detector, elasticsearch_writer, data_extraction.  
  - `config/`: Filebeat, Logstash pipeline.  
  - `docker/`: docker-compose cho ELK.  
  - Ứng dụng desktop: `run_simulation_app.py` (PySide6) – điều khiển train, detection, reset, xem thống kê và timeline.

**Nguồn tham khảo:**  
- [README.md](../README.md) – Thành phần chính  
- [TASK_HOAN_THANH_SIEM_ML.md](TASK_HOAN_THANH_SIEM_ML.md) – Kiến trúc từng phần, file/script liên quan

---

## 4. Thiết kế và triển khai

- **Dataset:** Synthetic (generate_synthetic_logs.py), Russell Mitchell (auth.log), Kaggle SSH; gộp qua `merge_training_datasets.py` → `unified_ssh_dataset.csv`.
- **Chuẩn hóa:** Schema thống nhất (STANDARD_COLS), nhãn `is_attack` boolean; model lưu `.joblib` với tên `ssh_attack_model.joblib`.
- **Pipeline detection:** Đọc log từ ES hoặc file → extract → preprocess (cùng đặc trưng với training) → load model → predict → ghi ml-alerts (timestamp, source_ip, ml_anomaly, ml_model).

**Nguồn tham khảo:**  
- [TASK_HOAN_THANH_SIEM_ML.md](TASK_HOAN_THANH_SIEM_ML.md) – Chuẩn hóa schema, định dạng model  
- [DANH_GIA_VA_DE_XUAT_CAI_TIEN.md](DANH_GIA_VA_DE_XUAT_CAI_TIEN.md) – Bảng chức năng đã có

---

## 5. Kết quả và đánh giá

- **Chức năng đạt được:** Thu thập log (Filebeat/Logstash), parse SSH/web, train unified model, detection online, ghi ml-alerts, xem trên Kibana; ứng dụng desktop (train/detection/reset, thống kê, timeline).
- **Chất lượng:** Có time-split, metrics (precision, recall, F1, ROC-AUC), lưu JSON; xử lý mất cân bằng lớp (SMOTE/undersample), tùy chọn GridSearchCV.
- **Điểm mạnh / điểm yếu / hướng cải thiện:** Dùng trực tiếp bảng trong [DANH_GIA_DU_AN_ELKShield.md](../DANH_GIA_DU_AN_ELKShield.md) (mục 2, 3, 4) và [DANH_GIA_VA_DE_XUAT_CAI_TIEN.md](DANH_GIA_VA_DE_XUAT_CAI_TIEN.md).

---

## 6. Hướng dẫn cài đặt và chạy (phục vụ demo)

- **Yêu cầu:** Python 3, Docker (ELK), pip (PySide6, pandas, scikit-learn, elasticsearch, joblib, …). Có thể dùng `requirements.txt` nếu có.
- **Chạy ELK:** `docker-compose -f docker/...` (theo README/docker trong repo).
- **Chạy ứng dụng desktop:** `python run_simulation_app.py` (cài PySide6).
- **Luồng demo đề xuất:**  
  1. Khởi động ELK, Filebeat (nếu dùng log thật).  
  2. Chọn dataset và Train (Unified / Synthetic / Russell / Train CSV).  
  3. Chạy Detection (test.log hoặc từ Elasticsearch).  
  4. Mở Kibana → index `ml-alerts-*` → xem cảnh báo theo thời gian, source_ip.

**Nguồn tham khảo:**  
- [README.md](../README.md) – Hướng dẫn nhanh, chạy production, yêu cầu tài nguyên  
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) – Xử lý lỗi thường gặp  
- [HUONG_DAN_DASHBOARD_KIBANA.md](HUONG_DAN_DASHBOARD_KIBANA.md), [HUONG_DAN_ALERTING_KIBANA.md](HUONG_DAN_ALERTING_KIBANA.md) – Dashboard và cảnh báo Kibana

---

## 7. Kết luận và hướng phát triển

- **Kết luận:** Hệ thống đạt mục tiêu đồ án: tích hợp ELK + ML, pipeline offline training + online detection, ghi cảnh báo lên Kibana; phù hợp demo và mở rộng (thêm log type, bảo mật ELK, inference API, near real-time).
- **Hướng phát triển:** Kiểm thử tự động, bảo mật ELK (xpack, TLS), API inference có xác thực, pipeline web thống nhất với SSH, dashboard Kibana mẫu, cảnh báo tự động (Kibana Alerting).

**Nguồn tham khảo:**  
- [DANH_GIA_DU_AN_ELKShield.md](../DANH_GIA_DU_AN_ELKShield.md) – Chấm điểm, kết luận ngắn  
- [DANH_GIA_VA_DE_XUAT_CAI_TIEN.md](DANH_GIA_VA_DE_XUAT_CAI_TIEN.md) – Đề xuất cải thiện theo mức ưu tiên

---

## 8. Câu dùng khi thuyết trình (demo)

> *"The system uses historical SSH datasets to train a machine learning model offline. The trained model is then deployed into a real-time ELK-based SIEM pipeline to detect attacks from live logs."*

*(Trích từ [TASK_HOAN_THANH_SIEM_ML.md](TASK_HOAN_THANH_SIEM_ML.md).)*

---

## Ghi chú

- Các file **HUONG_DAN_THUC_HIEN_DU_AN.md**, **HUONG_DAN_CHAY.md**, **HUONG_DAN_DATASET_THAT_VA_PIPELINE.md** được README nhắc đến nhưng có thể không nằm trong repo; nội dung tương tự có thể lấy từ README, TASK_HOAN_THANH_SIEM_ML và TROUBLESHOOTING.
- Nếu cần sơ đồ kiến trúc: vẽ từ mô tả Offline (merge → train → model) và Online (log → ELK → extract → preprocess → model → ml-alerts → Kibana).
