# Bảo mật ELK Stack – Lab vs Production

Tài liệu này mô tả cách bảo mật Elasticsearch và Kibana khi triển khai ELKShield (xpack security, user/password, TLS). Cấu hình mặc định trong dự án dùng **HTTP không xác thực** phù hợp **môi trường lab**.

---

## 1. Lab (mặc định hiện tại)

- **Elasticsearch:** Chạy HTTP, port 9200, không user/password.
- **Kibana:** Kết nối ES không auth.
- **Filebeat / Logstash:** Gửi đến ES không credentials.
- **Phù hợp:** Máy local, demo, đồ án. **Không** dùng khi expose ra internet hoặc nhiều người dùng.

---

## 2. Production – Bật bảo mật

### 2.1. Elasticsearch (xpack security)

- Trong `docker-compose.yml` (hoặc file cấu hình ES), bật:
  - `xpack.security.enabled: true`
  - `xpack.security.http.ssl.enabled: true` (TLS) nếu cần.
- Tạo user: dùng `elasticsearch-users` hoặc API `POST /_security/user`.
- Ví dụ user cho ứng dụng: `elastic` (superuser) hoặc user chỉ quyền ghi index.

### 2.2. Kibana

- Cấu hình Kibana dùng user/password để đăng nhập ES:
  - `elasticsearch.username`, `elasticsearch.password` trong `kibana.yml` hoặc biến môi trường.
- Truy cập Kibana qua **HTTPS** nếu triển khai ngoài LAN.

### 2.3. Filebeat

- Trong `filebeat.yml`, output Elasticsearch:
  - `output.elasticsearch.username`, `output.elasticsearch.password`.
  - `output.elasticsearch.ssl.enabled: true` nếu ES bật TLS.

### 2.4. Logstash

- Output Elasticsearch trong `pipeline.conf` (hoặc cấu hình tương đương):
  - Thêm `user`, `password` trong plugin `elasticsearch`.
  - Nếu ES dùng HTTPS: `hosts => ["https://elasticsearch:9200"]`, bật SSL.

### 2.5. Script Python (data_extraction, elasticsearch_writer)

- Kết nối ES với auth:
  - `Elasticsearch([url], basic_auth=("user", "password"))` (elasticsearch-py).
  - Nếu TLS: `url = "https://..."`, có thể cần `verify_certs`, `ca_certs`.

---

## 3. So sánh nhanh

| Mục | Lab (hiện tại) | Production (đề xuất) |
|-----|----------------|----------------------|
| Xác thực ES/Kibana | Không | User/password (xpack) |
| TLS/HTTPS | Không | Bật cho ES, Kibana, Beats |
| Filebeat/Logstash → ES | Không auth | Basic auth (và TLS nếu cần) |
| Script Python → ES | HTTP | Basic auth (+ HTTPS) |

---

## 4. Tham khảo

- [Elasticsearch Security](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-settings.html)
- [Kibana Security](https://www.elastic.co/guide/en/kibana/current/using-kibana-with-security.html)
- [Filebeat Elasticsearch output](https://www.elastic.co/guide/en/beats/filebeat/current/elasticsearch-output.html) (username, password, ssl).

Sau khi bật bảo mật, cập nhật **HUONG_DAN_CHAY.md** với bước cấu hình user/password và (nếu có) TLS cho từng thành phần.
