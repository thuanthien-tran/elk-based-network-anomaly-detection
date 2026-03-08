# Near real-time detection (Detection theo chu kỳ)

Pipeline **[7] Detection online** chạy **một lần** (extract → preprocess → predict → ghi ml-alerts). Để có cảnh báo **gần real-time**, có thể chạy pipeline này **định kỳ** (ví dụ mỗi 1–5 phút) bằng cron (Linux/macOS) hoặc Task Scheduler (Windows).

## 1. Chạy detection theo chu kỳ

### Linux / macOS (cron)

Chạy detection mỗi 5 phút:

```bash
# Mo crontab
crontab -e

# Them dong (sua DUONG_DAN_ELKShield cho dung)
*/5 * * * * cd /path/to/ELKShield && python scripts/run_pipeline_detection.py >> logs/detection.log 2>&1
```

Tạo thư mục `logs` nếu chưa có: `mkdir -p logs`.

### Windows (Task Scheduler)

1. Mở **Task Scheduler** → Create Basic Task.
2. Trigger: **Daily** (hoặc Repeat task every **5 minutes** trong 1 day).
3. Action: **Start a program**
   - Program: `python` (hoặc đường dẫn đầy đủ tới `python.exe`)
   - Arguments: `scripts/run_pipeline_detection.py`
   - Start in: `D:\Do An\...\ELKShield` (thư mục gốc dự án)
4. Lưu task.

### Script wrapper (chạy tay hoặc gọi từ cron/Task Scheduler)

Trong thư mục gốc dự án, tạo file `run_detection_interval.bat` (Windows) hoặc `run_detection_interval.sh` (Linux/macOS):

**run_detection_interval.bat (Windows):**
```batch
@echo off
cd /d "%~dp0"
python scripts/run_pipeline_detection.py
```

**run_detection_interval.sh (Linux/macOS):**
```bash
#!/bin/bash
cd "$(dirname "$0")"
python scripts/run_pipeline_detection.py
```

Đặt lịch gọi script này mỗi 5 phút (cron hoặc Task Scheduler).

## 2. Luồng dữ liệu

- **Filebeat** (chạy liên tục) đọc `test.log` (hoặc auth.log, Apache) và gửi lên **Logstash** → **Elasticsearch** (index `test-logs-*`, `ssh-logs-*`, …).
- **Detection** (mỗi 5 phút) đọc log mới từ ES (hoặc fallback `test.log`) → preprocess → model → ghi **ml-alerts-***.
- Trên **Kibana**, xem ml-alerts và (tùy chọn) cấu hình **Alerting** để gửi email/webhook khi số lượng alert vượt ngưỡng (xem [HUONG_DAN_ALERTING_KIBANA.md](HUONG_DAN_ALERTING_KIBANA.md)).

## 3. Lưu ý

- **Độ trễ:** Cảnh báo xuất hiện trong vòng một chu kỳ (ví dụ 5 phút) sau khi log vào ES; không phải từng sự kiện trong mili giây.
- **Tài nguyên:** Chạy detection mỗi phút tốn CPU hơn; 5–15 phút thường đủ cho demo và giám sát nhẹ.
- **Inference API:** Nếu cần gần real-time hơn (từng batch log gửi qua HTTP), có thể dùng `inference_api.py` và một script/Logstash plugin gọi POST /predict rồi ghi kết quả lên ES; cách này cần thiết kế tích hợp riêng.
