# Troubleshooting – Xử lý lỗi thường gặp

## 1. Không có index `test-logs-*` / `ssh-logs-*`

**Triệu chứng:** Detection [7] hoặc data_extraction báo: `No indices match 'test-logs-*,ssh-logs-*'. Existing: ml-alerts-...`

**Nguyên nhân:** Filebeat chưa gửi log lên Elasticsearch, hoặc chưa chạy đủ lâu để tạo index.

**Cách xử lý:**

1. **Chạy Filebeat:** Trong DEMO.bat chọn **[2] Chạy Filebeat** và giữ cửa sổ mở; hoặc chạy thủ công từ `config/filebeat` với cấu hình trỏ tới `test.log`.
2. **Tạo log:** Chọn **[5] Tạo log mẫu mặc định** (hoặc [4] nhập số dòng) để ghi vào `test.log` (Desktop hoặc Documents). Đợi vài giây để Filebeat đọc và gửi lên Logstash → ES.
3. **Kiểm tra index:** Vào Kibana → Stack Management → Index Management (hoặc Dev Tools): `GET _cat/indices?v`. Nếu có `test-logs-YYYY.MM.DD` thì đã có dữ liệu.
4. **Fallback:** Pipeline detection có fallback đọc trực tiếp từ `C:\Users\<user>\Documents\test.log` (Windows) nếu không có index; kết quả vẫn chạy nhưng không qua ELK ingest.

---

## 2. Detection báo "Detected 0 anomalies" / 0 anomalies

**Triệu chứng:** Chạy [7] xong, báo "Detected 0 anomalies out of N records".

**Nguyên nhân có thể:**

- **Model và dữ liệu khác biệt:** Model unified (train từ Synthetic + Russell + Kaggle) có đặc trưng và phân bố khác với log trong `test.log` hoặc index hiện tại; model coi phần lớn là "normal".
- **Ngưỡng (threshold):** Với Isolation Forest / One-Class SVM, điểm anomaly phải vượt ngưỡng mới đánh dấu; ngưỡng có thể khá cao.

**Cách xử lý:**

1. **Tạo log tấn công rõ ràng:** Dùng [5] (2 normal + 5 attack) hoặc [4] với log có nhiều "Failed password", "invalid user" để tăng cơ hội model bật anomaly.
2. **Kiểm tra dữ liệu train:** Đảm bảo đã chạy [6]-[2] rồi [6]-[1] (unified) với dataset có cả normal và attack.
3. **Xem ml-alerts trên Kibana:** Dù 0 anomalies, toàn bộ bản ghi vẫn được ghi vào ml-alerts-* (trường `ml_anomaly`: true/false); filter `ml_anomaly: true` để xem nếu sau này có.
4. **Tùy chỉnh model:** Có thể train lại với dataset gần với log thật hơn (ví dụ thêm Russell Mitchell [6]-[3]) rồi chạy lại [7].

---

## 3. Filebeat không gửi log / index vẫn trống

**Triệu chứng:** Đã bật Filebeat nhưng Kibana không thấy index `test-logs-*` hoặc không có document mới.

**Cách xử lý:**

1. **Đường dẫn file log:** Trong `config/filebeat/filebeat.yml`, kiểm tra `paths` trỏ đúng tới `test.log` (ví dụ `C:\Users\...\Documents\test.log` hoặc `%USERPROFILE%\Desktop\test.log`). Trên Windows đường dẫn dùng `/` hoặc `\\`.
2. **Logstash đang chạy:** Docker phải có Logstash (port 5044). Kiểm tra: `docker ps` thấy container logstash.
3. **Filebeat registry:** Nếu đổi tên file hoặc path, xóa registry để Filebeat đọc lại từ đầu: xóa thư mục `config/filebeat/data` (hoặc chạy [1] Reset trong DEMO.bat có thể xóa registry).
4. **Quyền đọc file:** Đảm bảo user chạy Filebeat có quyền đọc file log.
5. **Xem log Filebeat:** Chạy Filebeat trong terminal (không -e hoặc xem file log) để thấy lỗi kết nối Logstash/ES.

---

## 4. Không ghi được lên Elasticsearch (elasticsearch_writer / connection refused)

**Triệu chứng:** "Cannot connect to Elasticsearch", "Connection refused", hoặc pipeline báo không ghi được ml-alerts.

**Cách xử lý:**

1. **ELK đang chạy:** `docker ps` kiểm tra Elasticsearch (9200), Kibana (5601). Khởi động: `cd docker && docker-compose up -d`.
2. **Host/port:** Script dùng `--host 127.0.0.1 --port 9200`; nếu ES chạy máy khác hoặc port khác thì truyền đúng tham số.
3. **Retry:** elasticsearch_writer và data_extraction có retry (3 lần); nếu ES khởi động chậm, chạy lại pipeline sau vài chục giây.
4. **Firewall:** Trên Windows/Linux đảm bảo không chặn port 9200 (localhost).

---

## 5. Kibana không thấy dữ liệu ml-alerts / Discover trống

**Triệu chứng:** Đã chạy [7] thành công nhưng Kibana Discover (index pattern `ml-alerts-*`) không có bản ghi.

**Cách xử lý:**

1. **Data view / Index pattern:** Tạo Data view (Kibana 8) hoặc Index pattern với `ml-alerts-*`, timestamp field `@timestamp`.
2. **Time range:** Mở rộng time range (ví dụ Last 24 hours hoặc Last 7 days); bản ghi mới có `@timestamp` theo giờ ghi.
3. **Refresh:** Bấm Refresh trên Discover; hoặc bật Auto-refresh (ví dụ 30s).
4. **Index thực có dữ liệu:** Dev Tools: `GET ml-alerts-*/_count` để xác nhận số document.

---

## 6. Lỗi encoding khi đọc file log (Apache / CSV)

**Triệu chứng:** Script đọc log báo lỗi Unicode, hoặc ký tự lạ.

**Cách xử lý:**

- **Apache / CSV:** Dùng tham số `--encoding utf-8` (hoặc `cp1252` trên Windows nếu file là Windows-1252). Ví dụ: `apache_log_to_csv.py --input ... --output ... --encoding utf-8`.
- **File log:** Lưu file log bằng UTF-8 khi có thể; hoặc chuyển mã trước khi chạy pipeline.

---

## 7. Model file not found / Chưa train

**Triệu chứng:** "Model file not found", "Chua co model: data/models/ssh_attack_model.joblib".

**Cách xử lý:**

- Chạy train trước: **[6] Train model** → **[1] Train UNIFIED** (cần đã chạy [2] Chuẩn bị Synthetic và có đủ file processed từ Russell/Kaggle nếu cần). Hoặc [6]-[3] Russell Mitchell, [6]-[4] CSV để có model tương ứng.
- Detection [7] dùng `data/models/ssh_attack_model.joblib` (unified); đảm bảo file này tồn tại sau khi train [6]-[1].

---

## 8. Tham khảo thêm

- **Dashboard & Cảnh báo:** [HUONG_DAN_DASHBOARD_KIBANA.md](HUONG_DAN_DASHBOARD_KIBANA.md), [HUONG_DAN_ALERTING_KIBANA.md](HUONG_DAN_ALERTING_KIBANA.md).
- **Bảo mật ELK:** [BAO_MAT_ELK.md](BAO_MAT_ELK.md).
- **Near real-time:** [NEAR_REALTIME_DETECTION.md](NEAR_REALTIME_DETECTION.md).
