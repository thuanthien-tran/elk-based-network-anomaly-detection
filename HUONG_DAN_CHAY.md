# Hướng dẫn chạy dự án ELKShield

Hướng dẫn ngắn gọn, từng bước để chạy hệ thống từ đầu đến cuối.

---

## Yêu cầu hệ thống

- **Docker Desktop** — phải **mở và chạy** trước khi chạy docker-compose (icon Docker trên taskbar, đợi "Docker Desktop is running")
- **Python 3.8+** (kiểm tra: `python --version`)
- **Filebeat** (có sẵn trong `config/filebeat/` hoặc tải từ elastic.co)

---

## Bước 1: Cài đặt lần đầu (chỉ chạy 1 lần)

Mở CMD tại **thư mục gốc** dự án, chạy:

```cmd
setup.bat
```

Hoặc thủ công:

```cmd
mkdir data\raw data\processed ml_models reports
python -m pip install -r requirements.txt
```

---

## Bước 2: Khởi động ELK Stack

```cmd
cd docker
docker-compose up -d
```

**Đợi 1-2 phút** để các container khởi động hoàn toàn.

**Kiểm tra:**
```cmd
docker ps
```

Phải thấy 3 container đang chạy:
- `elk-elasticsearch` (port 9200)
- `elk-logstash` (port 5044)
- `elk-kibana` (port 5601)

**Test Elasticsearch:**
```cmd
curl http://127.0.0.1:9200
```

**Mở Kibana:** http://localhost:5601

---

## Bước 3: Reset dữ liệu cũ (nếu muốn bắt đầu lại)

Nếu bạn muốn **reset lại từ đầu** để mô phỏng tấn công mới:

### Cách 1: Dùng script PowerShell (khuyến nghị - chắc chắn hơn)

```powershell
powershell -ExecutionPolicy Bypass -File reset_data.ps1
```

### Cách 2: Dùng script Batch

```cmd
reset_data.bat
```

**Lưu ý:** Script batch có thể không xóa được tất cả index nếu wildcard không hoạt động trên Windows CMD.

### Cách 3: Thủ công (chắc chắn nhất)

**Bước 1: List tất cả index để xem tên chính xác:**
```cmd
curl http://127.0.0.1:9200/_cat/indices?v
```

**Bước 2: Xóa từng index một (copy tên index từ bước 1):**
```cmd
curl -X DELETE http://127.0.0.1:9200/test-logs-2026.02.19_8psRgSZQdWuoFDH0a5YLA
curl -X DELETE http://127.0.0.1:9200/ml-alerts-2026.02.20_809RJNUjS3eGRvlvt2PlAg
curl -X DELETE http://127.0.0.1:9200/ml-alerts-2026.02.19_MUnyUwjfQLSWXqf5g4_41A
```

**Hoặc dùng PowerShell để xóa tất cả tự động:**
```powershell
# Get all test-logs indices
$indices = (Invoke-RestMethod -Uri "http://127.0.0.1:9200/_cat/indices/test-logs-*?h=index").Trim() -split "`n"
foreach ($idx in $indices) {
    if ($idx) { Invoke-RestMethod -Uri "http://127.0.0.1:9200/$idx" -Method Delete }
}

# Get all ml-alerts indices
$indices = (Invoke-RestMethod -Uri "http://127.0.0.1:9200/_cat/indices/ml-alerts-*?h=index").Trim() -split "`n"
foreach ($idx in $indices) {
    if ($idx) { Invoke-RestMethod -Uri "http://127.0.0.1:9200/$idx" -Method Delete }
}
```

**Bước 3: Kiểm tra lại:**
```cmd
curl http://127.0.0.1:9200/_cat/indices?v
```

Phải không còn `test-logs-*` và `ml-alerts-*`.

**Xóa file log cũ:**
- Xóa file `C:\Users\thuan\Desktop\test.log` (hoặc đường dẫn của bạn)

---

## Bước 4: Tạo file log với tấn công mô phỏng

Tạo file log mới, ví dụ: `C:\Users\thuan\Desktop\test.log`

**Dán nội dung sau** (bao gồm cả normal traffic và attack):

```
# Normal traffic
Jan 19 10:00:01 localhost sshd[1001]: Accepted password for user1 from 192.168.1.10 port 22 ssh2
Jan 19 10:00:05 localhost sshd[1002]: Accepted password for user2 from 192.168.1.11 port 22 ssh2
Jan 19 10:00:10 localhost sshd[1003]: Accepted password for user3 from 192.168.1.12 port 22 ssh2

# Brute force attack (nhiều failed login từ cùng 1 IP)
Jan 19 10:01:01 localhost sshd[2001]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
Jan 19 10:01:02 localhost sshd[2002]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
Jan 19 10:01:03 localhost sshd[2003]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
Jan 19 10:01:04 localhost sshd[2004]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
Jan 19 10:01:05 localhost sshd[2005]: Failed password for invalid user admin from 10.10.10.10 port 22 ssh2
Jan 19 10:01:06 localhost sshd[2006]: Failed password for invalid user root from 10.10.10.10 port 22 ssh2
Jan 19 10:01:07 localhost sshd[2007]: Failed password for invalid user root from 10.10.10.10 port 22 ssh2

# Normal traffic tiếp tục
Jan 19 10:02:01 localhost sshd[1004]: Accepted password for user4 from 192.168.1.13 port 22 ssh2
```

**Lưu ý:**
- IP `10.10.10.10` là attacker (nhiều failed login liên tục)
- IP `192.168.1.x` là normal users (successful login)
- ML sẽ detect `10.10.10.10` là anomaly vì có pattern brute force

---

## Bước 5: Cấu hình và chạy Filebeat

### 5.1 Sửa đường dẫn trong Filebeat config

Mở file: `config/filebeat/filebeat-test-simple.yml`

Sửa dòng `paths` cho đúng đường dẫn file log của bạn:
```yaml
paths:
  - C:/Users/thuan/Desktop/test.log
```

### 5.2 Chạy Filebeat

**QUAN TRỌNG:** Filebeat chỉ gửi những dòng được **thêm vào SAU KHI Filebeat khởi động**. Nếu bạn tạo file log trước khi chạy Filebeat, Filebeat sẽ không gửi nội dung cũ.

**Workflow đúng:**

1. **Xóa registry của Filebeat (nếu đã chạy trước đó):**
   ```cmd
   REM Dừng Filebeat trước (Ctrl+C nếu đang chạy)
   REM Xóa thư mục data để reset trạng thái đã đọc
   rmdir /s /q config\filebeat\data
   ```

2. **Chạy Filebeat:**
   Mở **cửa sổ CMD mới**, chạy (giữ cửa sổ này mở):
   ```cmd
   cd config\filebeat
   filebeat.exe -c filebeat-test-simple.yml -e
   ```

3. **Thêm dòng mới vào test.log SAU KHI Filebeat đang chạy:**
   ```cmd
   REM Mở file test.log và thêm dòng mới, ví dụ:
   echo Jan 19 12:00:01 localhost sshd[3001]: Failed password for invalid user root from 8.8.8.8 port 22 ssh2 >> C:\Users\thuan\Desktop\test.log
   ```

**Kết quả mong đợi trong log Filebeat:**
- `harvester started: 1`
- `events added: 1` (hoặc số dòng bạn thêm)
- `acked: 1` (hoặc số dòng bạn thêm)

**Tại sao phải xóa data?**
- Filebeat lưu trạng thái trong `config/filebeat/data/registry/`
- Nó nhớ đã đọc đến cuối file rồi
- Dù bạn reset Elasticsearch, Filebeat vẫn nghĩ "File này mình đọc xong rồi"
- Xóa `data` folder để Filebeat quên trạng thái cũ và đọc lại từ đầu

**Nếu Filebeat không gửi logs:**
- Kiểm tra log Filebeat có hiển thị `events added: 0` không → nghĩa là không có dòng mới
- **Giải pháp:** Thêm dòng mới vào file log SAU KHI Filebeat đang chạy
- Kiểm tra đường dẫn trong `filebeat-test-simple.yml` có đúng không

---

## Bước 6: Kiểm tra logs đã vào Elasticsearch

**QUAN TRỌNG:** Sau khi thêm dòng mới vào `test.log` (SAU KHI Filebeat đang chạy), đợi vài giây rồi kiểm tra.

**Kiểm tra indices:**
```cmd
curl http://127.0.0.1:9200/_cat/indices?v
```

Phải thấy index dạng `test-logs-*` với cột `docs.count` > 0.

**Kiểm tra chi tiết logs:**
```cmd
curl "http://127.0.0.1:9200/test-*/_search?size=5&pretty"
```

Phải thấy các log đã được index.

### Troubleshooting nếu không có logs

**Vấn đề: Filebeat hiển thị `events added: 0`**
- **Nguyên nhân:** Filebeat chỉ gửi những dòng được thêm SAU KHI nó khởi động
- **Giải pháp:**
  1. Xóa registry: `rmdir /s /q config\filebeat\data`
  2. Chạy lại Filebeat
  3. **Thêm dòng mới vào test.log SAU KHI Filebeat đang chạy**

**Vấn đề: Filebeat không chạy**
```cmd
REM Kiểm tra Filebeat có đang chạy không
tasklist | findstr filebeat

REM Nếu không có → Chạy Filebeat
cd config\filebeat
filebeat.exe -c filebeat-test-simple.yml -e
```

**Vấn đề: Logstash không nhận được data**
```cmd
REM Kiểm tra Logstash logs
docker logs elk-logstash --tail 50
```

Phải thấy log "Successfully started Logstash" và không có lỗi.

**Vấn đề: Filebeat config sai đường dẫn**
- Mở `config/filebeat/filebeat-test-simple.yml`
- Kiểm tra `paths` có đúng đường dẫn file log không
- Dùng forward slash `/` thay vì backslash `\` trong đường dẫn

---

## Bước 7: Chạy pipeline ML

Quay lại **thư mục gốc** dự án, chạy lần lượt 4 lệnh sau:

### 7.1 Extract logs từ Elasticsearch

```cmd
python scripts/data_extraction.py --index test-* --output data/raw/logs.csv --hours 999 --host 127.0.0.1 --port 9200
```

**Lưu ý:** Dùng `--hours 999` để lấy tất cả logs (không filter theo thời gian).

**Kết quả mong đợi:** "Extracted X log entries" (X > 0)

**Nếu ra 0 logs:**
- Kiểm tra lại Bước 6 (index có docs không)
- Kiểm tra timezone: script đã dùng UTC (đã fix)

### 7.2 Preprocess data

```cmd
python scripts/data_preprocessing.py --input data/raw/logs.csv --output data/processed/logs.csv --clean --extract-time --extract-ip --extract-attack
```

**Kết quả mong đợi:** 
- "Loaded X records"
- "Attack distribution: False X, True Y" (Y > 0 nếu có attack)
- "Processed data saved"

**Nếu lỗi "File is empty":**
- Quay lại Bước 7.1, đảm bảo extraction ra được logs

### 7.3 Train ML model và predict

```cmd
python scripts/ml_detector.py --input data/processed/logs.csv --train --model-type isolation_forest --model-file ml_models/model.pkl --output data/predictions.csv
```

**Hoặc với contamination cao hơn để detect mạnh hơn:**

```cmd
python scripts/ml_detector.py --input data/processed/logs.csv --train --model-type isolation_forest --model-file ml_models/model.pkl --output data/predictions.csv --contamination 0.3
```

**Kết quả mong đợi:** 
- "Detected X anomalies out of Y records"
- "Anomaly rate: Z%"

**Lưu ý:** 
- `--contamination 0.3` nghĩa là expect 30% là anomaly
- Nếu muốn detect mạnh hơn, tăng lên `0.4` hoặc `0.5`

### 7.4 Ghi kết quả ML vào Elasticsearch

```cmd
python scripts/elasticsearch_writer.py --input data/predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200
```

**Kết quả mong đợi:** "Successfully indexed X documents"

---

## Bước 8: Xem kết quả trong Kibana

1. **Mở Kibana:** http://localhost:5601

2. **Tạo Index Pattern (nếu chưa có):**
   - Vào **Stack Management** → **Index Patterns** → **Create index pattern**
   - Nhập: `ml-alerts-*`
   - Time field: `@timestamp`
   - Click **Create index pattern**

3. **Xem kết quả:**
   - Vào **Discover**
   - Chọn index pattern `ml-alerts-*`
   - **Filter:** `ml_anomaly: true` → xem các anomalies
   - **Filter:** `is_attack: true` → xem các attacks
   - **Filter:** `source_ip: 10.10.10.10` → xem logs từ attacker IP

4. **Phân tích:**
   - IP `10.10.10.10` (attacker) sẽ có `ml_anomaly: true` và `is_attack: true`
   - IP `192.168.1.x` (normal users) sẽ có `ml_anomaly: false` và `is_attack: false`

---

## Lỗi thường gặp và cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|------------|
| `docker-compose up -d` báo lỗi mount | File `pipeline.conf` là thư mục thay vì file | Đã fix: file đã được tạo đúng |
| `The system cannot find the file specified` khi chạy docker-compose | Docker Desktop chưa chạy | Mở Docker Desktop, đợi "Docker Desktop is running" |
| `docker ps` không thấy logstash | Logstash container không start được | Kiểm tra `docker logs elk-logstash` để xem lỗi |
| Không kết nối được Elasticsearch | Container chưa start hoặc sai host | Dùng `--host 127.0.0.1` (không dùng `localhost` trên Windows) |
| Filebeat không gửi log (`events added: 0`) | Filebeat chỉ gửi dòng được thêm SAU KHI nó khởi động | 1. Xóa registry: `rmdir /s /q config\filebeat\data`<br>2. Chạy lại Filebeat<br>3. **QUAN TRỌNG:** Thêm dòng mới vào test.log SAU KHI Filebeat đang chạy<br>4. Kiểm tra log Filebeat có `events added: X` (X > 0) |
| Không có index sau khi chạy Filebeat | Filebeat không chạy hoặc không có dòng mới | 1. Kiểm tra Filebeat đang chạy: `tasklist \| findstr filebeat`<br>2. Xem log Filebeat: phải thấy `events added: X` (X > 0)<br>3. Thêm dòng mới vào file log SAU KHI Filebeat đang chạy<br>4. Kiểm tra Logstash: `docker logs elk-logstash` |
| Extraction ra 0 logs | Index không có docs hoặc timezone mismatch | 1. Kiểm tra index: `curl http://127.0.0.1:9200/_cat/indices?v`<br>2. Kiểm tra docs: `curl "http://127.0.0.1:9200/test-*/_search?size=5&pretty"`<br>3. Dùng `--hours 999` để lấy tất cả<br>4. Đảm bảo Filebeat đã gửi logs thành công |
| Preprocessing lỗi "File is empty" | CSV từ extraction rỗng | Quay lại Bước 7.1, đảm bảo extraction ra được logs |
| ML không detect được attack | Contamination quá thấp hoặc không có pattern rõ ràng | Tăng `--contamination 0.3` hoặc `0.4`. Đảm bảo có nhiều failed login từ cùng IP |
| Thiếu thư viện Python | Chưa cài dependencies | Chạy: `python -m pip install -r requirements.txt` |

---

## Tóm tắt workflow

```
1. setup.bat (1 lần)
   ↓
2. docker-compose up -d
   ↓
3. reset_data.bat (nếu muốn reset)
   ↓
4. Tạo test.log với attack logs
   ↓
5. Chạy Filebeat (giữ chạy)
   ↓
6. Kiểm tra index có logs
   ↓
7. Extract → Preprocess → Train ML → Write ES
   ↓
8. Xem trong Kibana (ml-alerts-*)
```

---

## Tips

- **Filebeat phải chạy liên tục** trong khi bạn muốn thu thập logs
- **QUAN TRỌNG:** Filebeat chỉ gửi những dòng được **thêm vào SAU KHI Filebeat khởi động**. Nếu tạo file log trước khi chạy Filebeat, Filebeat sẽ không gửi nội dung cũ
- **Workflow đúng:** Xóa registry → Chạy Filebeat → Thêm dòng mới vào file log → Filebeat tự động gửi
- **Xóa registry:** `rmdir /s /q config\filebeat\data` để reset trạng thái đã đọc của Filebeat
- **Kiểm tra log Filebeat:** Phải thấy `events added: X` (X > 0) khi thêm dòng mới
- **Kiểm tra index** trước khi chạy extraction để đảm bảo có dữ liệu
- **Script đã fix timezone** (UTC), không cần lo về timezone mismatch nữa
- **Dùng `--hours 999`** để lấy tất cả logs (không filter time)
- **Tăng `--contamination`** nếu muốn ML detect mạnh hơn (0.3 → 0.4 → 0.5)
- **Reset lại từ đầu** là cách tốt nhất để demo và test attack detection

---

## Mô phỏng tấn công hiệu quả

Để ML detect tốt, tạo log với pattern rõ ràng:

1. **Brute Force Attack:**
   - Nhiều failed login từ cùng 1 IP (`10.10.10.10`)
   - Liên tục trong thời gian ngắn
   - Thử nhiều username khác nhau (admin, root, test...)

2. **Normal Traffic:**
   - Successful login từ nhiều IP khác nhau
   - Rải rác theo thời gian
   - Username hợp lệ

3. **Kết quả mong đợi:**
   - IP attacker (`10.10.10.10`) → `ml_anomaly: true`, `is_attack: true`
   - IP normal users → `ml_anomaly: false`, `is_attack: false`

---

**Chúc bạn chạy thành công và detect được attacks!** 🚀
