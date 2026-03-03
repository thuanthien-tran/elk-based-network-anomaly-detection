# Hướng dẫn thực hiện / Chạy demo ELKShield

Dành cho sinh viên — vừa đủ chi tiết để làm theo, không dài dòng.

---

## Mục tiêu dự án

Hệ thống thu thập log (SSH, web), đưa vào ELK Stack, dùng Machine Learning để phát hiện bất thường (ví dụ brute force). Kết quả xem trên Kibana.

**Luồng tổng quát:** File log → Filebeat → Logstash → Elasticsearch → Script Python (extract, xử lý, train ML, ghi lại) → Elasticsearch (index ml-alerts) → Kibana.

---

## Yêu cầu trước khi chạy

- **Docker Desktop** đã cài và đang chạy (mở app, đợi "Docker Desktop is running").
- **Python 3.8+** (mở CMD gõ `python --version`).
- **Filebeat**: dùng bản trong `config\filebeat\` (có sẵn `filebeat.exe` và `filebeat-test-simple.yml`).

---

## Cách 1: Chạy bằng script tự động (nhanh)

1. Mở thư mục **Demo**, chạy file **`CHAY_DEMO.bat`**.
2. Chọn lần lượt các mục trong menu (theo thứ tự gợi ý bên dưới).
3. Lần đầu: chọn **1** (Cài đặt) → **2** (Khởi động ELK) → **3** (Reset) → **4** (Chạy Filebeat, giữ cửa sổ mở) → **5** (Tạo log mẫu) → đợi vài giây → **6** (Chạy pipeline ML) → **7** (Mở Kibana).

Script sẽ nhắc bạn làm từng bước; làm xong bước trước rồi mới chọn bước sau.

---

## Cách 2: Chạy thủ công từng bước

### Bước 1 — Cài đặt lần đầu (chỉ làm một lần)

Tại **thư mục gốc** dự án (chứa `setup.bat`):

```cmd
setup.bat
```

Hoặc: tạo thư mục `data\raw`, `data\processed`, `ml_models`, `reports` và chạy `python -m pip install -r requirements.txt`.

---

### Bước 2 — Khởi động ELK Stack

```cmd
cd docker
docker-compose up -d
```

Đợi 1–2 phút. Kiểm tra: `docker ps` — phải thấy 3 container (elasticsearch, logstash, kibana). Mở trình duyệt: **http://localhost:5601** (Kibana).

---

### Bước 3 — Reset dữ liệu (khi muốn chạy lại từ đầu)

Chạy `reset_data.bat` hoặc `reset_data.ps1` ở thư mục gốc. Hoặc xóa index thủ công trong Kibana: Stack Management → Index Management → xóa `test-logs-*` và `ml-alerts-*`.

Sau đó xóa thư mục `config\filebeat\data` (nếu có) để Filebeat đọc lại file log từ đầu.

---

### Bước 4 — Chuẩn bị file log và Filebeat

- Tạo file log, ví dụ: `C:\Users\<TenMay>\Desktop\test.log`.
- Mở `config\filebeat\filebeat-test-simple.yml`, sửa `paths` cho đúng đường dẫn file vừa tạo (dùng dấu `/`).
- **Chạy Filebeat** (giữ cửa sổ CMD mở):

  ```cmd
  cd config\filebeat
  filebeat.exe -c filebeat-test-simple.yml -e
  ```

- **Quan trọng:** Filebeat chỉ gửi những dòng **thêm vào sau khi** nó đã chạy. Vì vậy: chạy Filebeat trước, sau đó mới thêm nội dung vào `test.log` (ghi tay hoặc dùng lệnh `echo ... >> test.log`).

---

### Bước 5 — Tạo log mẫu (sau khi Filebeat đang chạy)

Thêm vào `test.log` vài dòng bình thường và vài dòng tấn công mô phỏng, ví dụ:

- Bình thường: `Accepted password for user1 from 192.168.1.10 ...`
- Tấn công: nhiều dòng `Failed password for invalid user admin from 10.10.10.10 ...` (cùng IP 10.10.10.10).

Trong log Filebeat phải thấy `events added: X` với X > 0.

---

### Bước 6 — Chạy pipeline ML

Tại **thư mục gốc** dự án, chạy lần lượt:

```cmd
python scripts/data_extraction.py --index test-* --output data/raw/logs.csv --hours 999 --host 127.0.0.1 --port 9200
python scripts/data_preprocessing.py --input data/raw/logs.csv --output data/processed/logs.csv --clean --extract-time --extract-ip --extract-attack
python scripts/ml_detector.py --input data/processed/logs.csv --train --model-type isolation_forest --model-file ml_models/model.pkl --output data/predictions.csv
python scripts/elasticsearch_writer.py --input data/predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200
```

---

### Bước 7 — Xem kết quả

- Vào Kibana: http://localhost:5601  
- Tạo index pattern `ml-alerts-*` (Stack Management → Index Patterns).  
- Vào Discover, chọn `ml-alerts-*`, filter `ml_anomaly: true` để xem các bản ghi ML đánh dấu bất thường.

---

## Lưu ý nhanh

- Filebeat phải chạy **trước**, sau đó mới thêm dòng vào file log thì log mới vào Elasticsearch.
- Nếu không thấy index `test-logs-*`: kiểm tra Filebeat có chạy không, đường dẫn trong `filebeat-test-simple.yml` có đúng không, và đã xóa `config\filebeat\data` chưa (khi muốn đọc lại từ đầu).
- Nếu extraction ra 0 bản ghi: kiểm tra `curl http://127.0.0.1:9200/_cat/indices?v` đã có index và có docs chưa; có thể dùng `--hours 999` để lấy toàn bộ log.

---

## Tóm tắt thứ tự

1. Cài đặt (setup)  
2. Khởi động ELK (docker-compose)  
3. Reset (nếu cần) + xóa `config\filebeat\data`  
4. Chạy Filebeat  
5. Thêm log mẫu vào file  
6. Chạy 4 lệnh Python (extract → preprocess → train → write ES)  
7. Xem trong Kibana (ml-alerts-*)

Chi tiết đầy đủ hoặc gặp lỗi: xem file **HUONG_DAN_CHAY.md** ở thư mục gốc dự án.
