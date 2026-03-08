# Kibana – Dashboard & Saved Objects

Thư mục này dùng để lưu **dashboard Kibana** và **saved objects** (index pattern/data view, visualization) export từ Kibana, giúp chia sẻ và khôi phục cấu hình giữa các môi trường.

## Nội dung đề xuất

- **Index pattern / Data view:** `ml-alerts-*`, `test-logs-*`, `ssh-logs-*`, `web-logs-*`
- **Dashboard:** ML Alerts (theo thời gian, theo `ml_model`, theo `source_ip`)

## Cách tạo và export

1. Vào Kibana (http://localhost:5601) → **Stack Management** → **Saved Objects**.
2. Tạo dashboard và visualization theo hướng dẫn: [docs/HUONG_DAN_DASHBOARD_KIBANA.md](../../docs/HUONG_DAN_DASHBOARD_KIBANA.md).
3. Sau khi tạo xong, chọn dashboard (và các object liên quan) → **Export** → lưu file `.ndjson` vào thư mục này (ví dụ: `ml-alerts-dashboard.ndjson`).

## Cách import

- **Kibana UI:** Stack Management → Saved Objects → **Import** → chọn file `.ndjson` trong `config/kibana/`.
- **API:** `POST /api/saved_objects/_import` (Kibana 8) với file NDJSON.

Chi tiết từng bước: [docs/HUONG_DAN_DASHBOARD_KIBANA.md](../../docs/HUONG_DAN_DASHBOARD_KIBANA.md).
