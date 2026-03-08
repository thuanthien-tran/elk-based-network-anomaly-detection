# Đánh giá và đề xuất cải thiện ELKShield

**Mục đích:** Xem xét dự án có đủ chức năng cho một hệ thống ELKShield (SIEM + ML) hay chưa, và đề xuất hướng cải thiện.

---

## 1. Kết luận nhanh

**Dự án đã có đầy đủ chức năng cốt lõi cho một ELKShield** (thu thập log → parse → đặc trưng → ML train/detect → cảnh báo trên Kibana). Đủ để demo, đồ án và phát triển tiếp. Để gần với hệ thống “production-ready” hoặc “đầy đủ tính năng”, cần bổ sung một số mảng (cảnh báo tự động, dashboard, bảo mật API/ELK, pipeline web thống nhất).

---

## 2. Chức năng đã có (đủ cho ELKShield cơ bản)

| Nhóm | Chức năng | Trạng thái |
|------|-----------|------------|
| **Thu thập & parse log** | Filebeat → Logstash (Grok SSH + web, rule brute-force/SQLi/XSS) → ES (test-logs-*, ssh-logs-*, web-logs-*) | ✅ Có |
| **Trích xuất & tiền xử lý** | data_extraction (ES/fallback file), data_preprocessing (SSH + web, --log-type) | ✅ Có |
| **ML** | Train: RF / Isolation Forest / One-Class SVM; unified (gộp Synthetic + Russell + Kaggle); time-split, xử lý mất cân bằng, metrics JSON | ✅ Có |
| **Detection online** | [7] Extract → preprocess → load unified model → predict → ghi ml-alerts-* | ✅ Có |
| **Kết quả trên Kibana** | Index ml-alerts-* với @timestamp, source_ip, ml_anomaly, ml_anomaly_score, **ml_model** (phân biệt unified/russellmitchell/csv/...) | ✅ Có |
| **Demo & tài liệu** | DEMO.bat (reset, Filebeat, Kibana, tạo log, train [gộp / từng dataset], detection, demo nhanh); README, TASK, BAO_MAT_ELK, hướng dẫn chạy | ✅ Có |
| **API inference** | inference_api.py (Flask, /predict, /health) | ✅ Có |
| **Đề xuất phòng thủ** | defense_recommendations gắn với từng bản ghi ml-alerts | ✅ Có |
| **Kiểm thử** | tests/ (ml_detector, data_preprocessing, data_extraction, integration) | ✅ Có |

---

## 3. Chức năng còn thiếu / chưa đồng bộ

| Nhóm | Thiếu gì | Ảnh hưởng |
|------|----------|-----------|
| **Cảnh báo tự động** | Không có rule Kibana Alerting / Watcher / Elastalert trên ml-alerts-* hoặc severity | Không tự gửi mail/Slack khi có anomaly |
| **Dashboard Kibana** | Không có dashboard mẫu export (JSON) trong repo | User phải tự tạo view cho ml-alerts, ssh-logs, web-logs |
| **Bảo mật API** | inference_api.py không có auth (API key / Basic) | Rủi ro nếu mở ra ngoài |
| **Bảo mật ELK** | Docker đang tắt xpack (HTTP, không user/pass) | Đúng cho lab; chưa đủ cho production |
| **Pipeline web** | Có Grok + preprocess web nhưng chưa có luồng “train + ghi ml-alerts” thống nhất như SSH (unified) | Web log chưa tận dụng hết ML → ml-alerts |
| **Real-time thật** | Detection [7] chạy batch (theo lần); chưa có trigger theo sự kiện (ví dụ mỗi N dòng log mới) | Cảnh báo theo “đợt” chứ chưa từng sự kiện |

---

## 4. Đề xuất cải thiện (theo mức độ ưu tiên)

### Mức 1 – Nên làm (nâng trải nghiệm và tính tin cậy)

1. **Dashboard Kibana mẫu**
   - Tạo 1–2 dashboard (ml-alerts theo thời gian, theo ml_model, theo source_ip; có thể thêm ssh-logs/web-logs).
   - Export JSON vào `config/kibana/` hoặc `docs/`, thêm hướng dẫn import trong README/DEMO.

2. **Cảnh báo đơn giản**
   - Một rule Kibana Alerting: khi count ml-alerts (hoặc ml_anomaly = true) trong 5–15 phút > ngưỡng → gửi (email hoặc webhook). Hoặc dùng Watcher nếu dùng ES stack cũ.
   - Ghi rõ trong docs: “Bật cảnh báo: vào Kibana → Stack Management → Rules”.

3. **Bảo mật API inference**
   - Thêm API key hoặc Basic auth cho `inference_api.py` (biến môi trường hoặc config); ghi trong README/BAO_MAT.

### Mức 2 – Nên làm nếu muốn “đầy đủ tính năng”

4. **Thống nhất pipeline web với SSH**
   - Cho phép train model từ web log (hoặc web+SSH) và ghi kết quả vào ml-alerts-* (có thể thêm trường log_type hoặc dùng chung ml_model).
   - Cập nhật DEMO hoặc script “run_pipeline_web” để có bước: preprocess web → train (hoặc dùng model có sẵn) → elasticsearch_writer với ml_model (ví dụ "web").

5. **Bảo mật ELK cho môi trường thật**
   - Làm theo docs/BAO_MAT_ELK.md: bật xpack, user/password, TLS; cấu hình Filebeat/Logstash/Python client.
   - Trong README thêm mục “Chạy production” trỏ tới BAO_MAT_ELK.

6. **Robustness**
   - Retry/backoff khi kết nối ES (data_extraction, elasticsearch_writer); kiểm tra encoding (UTF-8) khi đọc file log; ghi trong README yêu cầu RAM/disk khi dataset lớn.

### Mức 3 – Tùy chọn (nâng cao)

7. **Real-time hơn**
   - Dùng inference API: Logstash (hoặc script) mỗi batch N dòng gọi POST /predict rồi ghi ml-alerts; hoặc cron chạy [7] mỗi 1–5 phút. Ghi rõ trong tài liệu “Near real-time”.

8. **CI cho kiểm thử**
   - GitHub Actions (hoặc script local) chạy `pytest tests/` khi push/PR; có thể thêm test dùng ES mock hoặc testcontainers nếu cần.

9. **Sổ tay vận hành**
   - Troubleshooting: “Không có index test-logs-*”, “0 anomalies”, “Filebeat không gửi log”, “Kibana không thấy ml-alerts”; và checklist triển khai (Docker, Filebeat, [6]-[1], [7]).

---

## 5. Tóm tắt

- **Đã đủ cho ELKShield:** Thu thập log (Filebeat/Logstash), parse đa loại (SSH/web), train ML (unified + từng dataset), detection online ghi ml-alerts, phân biệt nguồn bằng ml_model, xem trên Kibana, có API inference và tài liệu/demo.
- **Cải thiện đề xuất:** Thêm dashboard Kibana mẫu + cảnh báo đơn giản + bảo mật API (mức 1); thống nhất pipeline web, bảo mật ELK, robustness (mức 2); real-time/CI/troubleshooting (mức 3).

**Đã thực hiện (cập nhật):** Mức 1–3 đã được triển khai: hướng dẫn Dashboard & Alerting Kibana, bảo mật API (--api-key, --basic-auth), pipeline web --train --write-es, README Chạy production + robustness (retry ES, encoding/RAM/disk), near real-time (script + doc), CI GitHub Actions (pytest), tài liệu TROUBLESHOOTING. Chi tiết trong README và từng file trong docs/.
