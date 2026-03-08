# Hướng dẫn tạo Dashboard Kibana cho ELKShield

Dashboard giúp xem nhanh **ml-alerts** (cảnh báo ML) theo thời gian, theo model/pipeline và theo nguồn (source_ip).

## 1. Tạo Data view (Index pattern)

1. Mở **Kibana** → **Stack Management** (menu trái) → **Data Views** (Kibana 8) hoặc **Index Patterns** (Kibana 7).
2. **Create data view**:
   - **Name:** `ML Alerts`
   - **Index pattern:** `ml-alerts-*`
   - **Timestamp field:** `@timestamp`
3. Lưu. Có thể tạo thêm: `test-logs-*`, `ssh-logs-*`, `web-logs-*` nếu bạn dùng log từ Filebeat.

## 2. Tạo các Visualization

### 2.1. Số lượng ml-alerts theo thời gian

1. **Analytics** → **Discover** (hoặc **Visualize Library**).
2. Chọn data view **ML Alerts**.
3. **Create visualization** (hoặc **Lens**):
   - **Chart type:** Line hoặc Area.
   - **Horizontal axis:** `@timestamp` (Date Histogram, interval Auto hoặc 1h).
   - **Vertical axis:** Count.
   - **Title:** "ML Alerts over time".
4. **Save** → đặt tên ví dụ: "ML Alerts - Time series".

### 2.2. Phân bố theo ml_model

1. **Create visualization** (Lens hoặc Aggregation based):
   - **Chart type:** Bar (vertical) hoặc Pie.
   - **Breakdown / Segment:** Field `ml_model` (keyword).
   - **Metric:** Count.
   - **Title:** "ML Alerts by model".
4. **Save** → "ML Alerts by model".

### 2.3. Top source_ip (nhiều cảnh báo nhất)

1. **Create visualization**:
   - **Chart type:** Bar (horizontal).
   - **Breakdown:** Field `source_ip`, Top 10.
   - **Metric:** Count.
   - **Title:** "Top source IPs (ml-alerts)".
4. **Save** → "ML Alerts - Top source IPs".

### 2.4. Chỉ anomaly (ml_anomaly = true)

1. Trong Discover hoặc Lens, thêm **Filter:** `ml_anomaly: true`.
2. Tạo visualization tương tự (time series hoặc bar) với filter này → **Save** "ML Anomalies only".

## 3. Tạo Dashboard

1. **Dashboard** → **Create dashboard**.
2. **Add from library** → chọn lần lượt các visualization đã lưu (ML Alerts - Time series, ML Alerts by model, ML Alerts - Top source IPs, ML Anomalies only).
3. Sắp xếp layout (kéo thả), chỉnh time range chung (ví dụ Last 24 hours).
4. **Save** → đặt tên: "ELKShield - ML Alerts".

## 4. Export để lưu vào repo

1. **Stack Management** → **Saved Objects**.
2. Tìm và chọn dashboard **ELKShield - ML Alerts** (chọn cả các visualization và data view liên quan).
3. **Export** → chọn **Export included objects** (để có cả dependencies).
4. Lưu file `.ndjson` vào thư mục dự án: `config/kibana/ml-alerts-dashboard.ndjson`.

Sau này có thể **Import** lại từ file này (Stack Management → Saved Objects → Import).

## 5. Gợi ý nhanh

- **Time range:** Đặt "Last 24 hours" hoặc "Last 7 days" để tránh dashboard trống nếu chưa có dữ liệu.
- **Refresh:** Bật Auto-refresh (ví dụ 30s) nếu đang chạy Detection [7] liên tục.
- **Filter:** Trong dashboard có thể thêm filter mặc định, ví dụ `ml_model: "unified"` để chỉ xem cảnh báo từ model unified.
