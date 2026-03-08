# Hướng dẫn tạo Cảnh báo (Alerting) trên Kibana cho ELKShield

Khi số lượng **ml-alerts** (hoặc bản ghi anomaly) trong một khoảng thời gian vượt ngưỡng, Kibana có thể gửi thông báo qua **email** hoặc **webhook** (Slack, Teams, v.v.).

## Điều kiện

- Kibana 8.x (Alerting có sẵn trong Stack).
- Đã có index `ml-alerts-*` và đã tạo **Data view** `ml-alerts-*` (xem [HUONG_DAN_DASHBOARD_KIBANA.md](HUONG_DAN_DASHBOARD_KIBANA.md)).

## 1. Mở Rule Alerting

1. **Kibana** → **Stack Management** (menu trái) → **Rules** (trong mục Alerts and Actions / Alerting).
2. Hoặc **Alerts** → **Rules** → **Create rule**.

## 2. Tạo Rule mới

### Bước 1: Chọn loại rule

- Chọn **Elasticsearch query** (hoặc **Threshold** nếu giao diện có sẵn kiểu này) để dựa trên truy vấn ES.

### Bước 2: Define the rule

- **Name:** `ELKShield - ML Alerts threshold`
- **Check every:** 5m hoặc 15m (tùy bạn).
- **Notify:** Chỉ khi số bản ghi vượt ngưỡng.

### Bước 3: Query và ngưỡng

- **Index:** Chọn data view hoặc index pattern `ml-alerts-*`.
- **Query (KQL hoặc DSL):**
  - Đếm tất cả ml-alerts trong cửa sổ thời gian: để trống filter hoặc `*`.
  - Hoặc chỉ anomaly: thêm filter `ml_anomaly: true`.
- **Condition (Threshold):**
  - **Aggregation:** Count.
  - **Threshold:** Greater than (>) — ví dụ **5** (cảnh báo khi có hơn 5 bản ghi trong 5 phút).

### Bước 4: Actions (gửi thông báo)

- **Create connector** (nếu chưa có):
  - **Email:** Nhập SMTP và địa chỉ email nhận.
  - **Webhook:** URL (ví dụ Slack Incoming Webhook, Microsoft Teams webhook). Method POST, body có thể dùng template: `{"text": "ELKShield: {{count}} ml-alerts in last 5m"}`.
- Gắn connector vào rule: **Add action** → chọn connector → lưu.

### Bước 5: Save

- **Save** rule. Rule sẽ chạy theo lịch (every 5m/15m) và gửi cảnh báo khi điều kiện thỏa.

## 3. Kiểm tra

- Vào **Rules** → mở rule vừa tạo → xem **Run history** / **Last run**.
- Cố ý tạo nhiều ml-alerts (chạy [7] Detection hoặc ghi thử) rồi đợi chu kỳ rule để xác nhận alert được gửi.

## 4. Gợi ý

- **Ngưỡng:** Bắt đầu với 5–10; chỉnh theo môi trường để tránh quá nhiều false positive.
- **Chỉ anomaly:** Dùng filter `ml_anomaly: true` nếu chỉ muốn cảnh báo khi có bản ghi được model đánh là bất thường.
- **Connector:** Nếu không cấu hình email/SMTP, dùng **Webhook** với URL Slack/Teams để nhận thông báo nhanh.
