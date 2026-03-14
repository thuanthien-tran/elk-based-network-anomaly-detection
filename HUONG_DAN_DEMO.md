# Hướng dẫn chạy demo ELKShield (dễ hiểu nhất)

## Demo nhanh — 2 bước

### Bước 1: Mở ứng dụng

Trong thư mục gốc của project, chạy:

```bash
python elkshield.py
```

(Hoặc: `python run_simulation_app.py`)

Cửa sổ **ELKShield Unified Security Platform** sẽ mở. Nút **Start SIEM** đã được chọn sẵn.

---

### Bước 2: Chạy luồng giám sát

Bấm nút **▶ Start Security Workflow** (nút xanh lá lớn bên dưới).

Hệ thống sẽ tự động chạy:

1. Kiểm tra ELK (Elasticsearch)
2. Load mô hình ML
3. Thu thập log (ghi test log nếu cần)
4. Trích xuất đặc trưng
5. Phát hiện tấn công (ML)
6. Ghi alert lên Elasticsearch
7. Đề xuất phòng thủ
8. Mở Kibana (Dashboard)

Kết quả hiển thị ở **Terminal Output** (khung bên phải). Khi xong, trình duyệt có thể tự mở Kibana.

---

## Xem alert sau khi chạy

- **SOC Dashboard** — Mở Kibana tổng quan.
- **Alert Feed** — Xem danh sách alert (index `ml-alerts`).
- **Defense Strategy** — Xem đề xuất phòng thủ (block IP, v.v.).

---

## Yêu cầu trước khi demo (bắt buộc)

1. **Elasticsearch đang chạy** (port 9200)  
   - Ví dụ: `docker-compose up -d` trong thư mục `docker/`.  
   - Kiểm tra: mở http://127.0.0.1:9200 trên trình duyệt.

2. **Đã train model ít nhất một lần**  
   - Trong app: chọn **Train Global Model** → bấm **Start Security Workflow**, đợi chạy xong.  
   - Nếu chưa train, bước 2 sẽ báo "Chưa có model".

3. **Cài thư viện ghi dữ liệu lên Elasticsearch** (để bước 6 không báo lỗi, Kibana mới có alert):
   ```bash
   pip install pandas "elasticsearch>=8,<9"
   ```
   - Nếu bạn dùng Elasticsearch 7.x: `pip install "elasticsearch>=7,<8"`.  
   - Nếu bước 6 vẫn lỗi, xem Terminal Output trong app — dòng lỗi màu đỏ sẽ gợi ý nguyên nhân (thiếu thư viện, sai phiên bản, v.v.).

---

## Nếu Kibana không có dữ liệu (bước 6 báo "Ghi ES cảnh báo: lỗi")

Nghĩa là bước **Write Alert ES** thất bại, nên index `ml-alerts-*` trống. Làm lần lượt:

### Bước A: Cài đủ thư viện (xem trên)

```bash
pip install pandas "elasticsearch>=8,<9"
```

### Bước B: Ghi alert thủ công (sau khi đã chạy Start SIEM và có file `data/predictions.csv`)

Mở terminal **trong thư mục gốc project** và chạy:

```bash
python scripts/elasticsearch_writer.py --input data/predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200 --model-name unified
```

- Nếu thành công, sẽ in dạng: `Created index: ml-alerts-2026.02.xx-...` và `Prepared N documents for indexing`.
- Sau đó trong app bấm **Alert Feed** hoặc **SOC Dashboard** → chọn data view `ml-alerts-*` trong Kibana Discover để xem alert.

### Bước C: Kiểm tra Elasticsearch

- Truy cập http://127.0.0.1:9200 — phải thấy JSON thông tin cluster.  
- Nếu không, khởi động lại ELK (Docker hoặc cài bản standalone).

---

## Tóm tắt 1 dòng

**Cài Elasticsearch + train model + `pip install pandas "elasticsearch>=8,<9"` → Mở app → bấm "▶ Start Security Workflow" → (nếu bước 6 lỗi thì chạy tay lệnh Bước B).**
