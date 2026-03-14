# Response Layer (SOAR direction)

Tầng **Response & Defense** — *Semi-Automated Response Framework*.

## Đã triển khai

- **Alert:** Index `ml-alerts-*`, Kibana Alerting (xem docs/HUONG_DAN_ALERTING_KIBANA.md).
- **Visualization:** Kibana dashboard, app desktop (Attacks Timeline, thống kê).
- **Suggest defense:** `defense_recommendations.py` + trường trong ml-alerts; nút "Xem đề xuất phòng thủ" trong app.

## Future (placeholder)

- **Auto block IP:** Gọi firewall/API block IP khi alert vượt ngưỡng → `auto_mitigation_stub.py`.
- **Firewall integration:** Cập nhật rule iptables/nftables hoặc cloud firewall.
- **IDS integration:** Gửi cảnh báo sang IDS hoặc SOAR platform.

Các file trong thư mục này là stub/placeholder cho giai đoạn sau.
