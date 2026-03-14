# Checklist cấu trúc 5 tầng – ELKShield

Kiểm tra từng task theo kiến trúc Research Paper (Data → SIEM → ML → Detection → Response).  
**Chú thích:** ✅ Đã hoàn thành | ⏳ Future / mở rộng sau | ➖ Không áp dụng (optional)

---

## 1. Data Layer (Heterogeneous Log Sources)

| # | Task | Trạng thái | Ghi chú / File |
|---|------|------------|----------------|
| 1.1 | SSH logs (auth, sshd) | ✅ | Filebeat `config/filebeat/filebeat.yml`; test.log; `data/russellmitchell/gather/` |
| 1.2 | System logs (syslog-style) | ✅ | Cùng pipeline Logstash, hỗ trợ SYSLOGTIMESTAMP |
| 1.3 | Network logs | ⏳ | Có thể thêm input Filebeat; hiện tập trung SSH + web |
| 1.4 | App logs (web server) | ✅ | Filebeat `log_type: web`; `data/apache-http-logs-master/` |
| 1.5 | Synthetic attack logs | ✅ | `scripts/generate_synthetic_logs.py`; app "Ghi log" → test.log |
| 1.6 | Public datasets | ✅ | Russell Mitchell, Kaggle (`data/ssh_anomaly_dataset.csv`), dataset1 (Twente) |
| 1.7 | Thu thập: Filebeat → Logstash:5044 | ✅ | Config Filebeat, Docker Logstash |

**Tổng Data Layer:** 6/7 ✅, 1 ⏳ (network logs mở rộng)

---

## 2. SIEM Layer (ELK Core – Hybrid SIEM)

| # | Task | Trạng thái | Ghi chú / File |
|---|------|------------|----------------|
| 2.1 | Log ingestion (Filebeat) | ✅ | `config/filebeat/filebeat.yml`, Chay_Filebeat.bat |
| 2.2 | Log parsing (Grok) | ✅ | `config/logstash/pipeline.conf` – SSH, HTTP |
| 2.3 | Enrichment (date, index_prefix, tags) | ✅ | Logstash date filter, `[@metadata][index_prefix]` |
| 2.4 | Rule-based detection (brute force) | ✅ | Logstash: Failed password / invalid user → is_attack, attack_type |
| 2.5 | Rule-based detection (SQLi, XSS) | ✅ | Logstash: regex trên request → is_attack, attack_type |
| 2.6 | Correlation (time window, IP aggregation) | ✅ | `scripts/data_preprocessing.py` |
| 2.7 | Storage – raw logs index | ✅ | test-logs-*, ssh-logs-*, web-logs-* |
| 2.8 | Storage – alert index (từ rule) | ➖ | Rule ghi is_attack vào log index; ML ghi ml-alerts-* |
| 2.9 | Visualization (Kibana) | ✅ | Discover, Dashboard; app "Mở Kibana", "View Alerts" |

**Tổng SIEM Layer:** 8/9 ✅ (2.8: alert từ rule nằm trong log index)

---

## 3. ML Layer (AI-Driven Threat Detection Engine)

### Offline

| # | Task | Trạng thái | Ghi chú / File |
|---|------|------------|----------------|
| 3.1 | Dataset aggregation | ✅ | `scripts/merge_training_datasets.py` – Synthetic + Russell + Kaggle + Custom |
| 3.2 | Feature engineering | ✅ | `scripts/data_preprocessing.py` – SSH + web features |
| 3.3 | Model training (RF, IF, OCSVM) | ✅ | `scripts/train_model.py`, `scripts/ml_detector.py` |
| 3.4 | Output model (ssh_attack_model.joblib) | ✅ | `data/models/ssh_attack_model.joblib` |
| 3.5 | LSTM / Deep Learning | ⏳ | Future work |

### Online

| # | Task | Trạng thái | Ghi chú / File |
|---|------|------------|----------------|
| 3.6 | Stream feature extraction | ✅ | Trong `run_pipeline_detection.py` (preprocess) |
| 3.7 | Real-time anomaly detection | ✅ | `scripts/run_pipeline_detection.py` – load model, predict |
| 3.8 | Behavioral analysis (time window, IP) | ✅ | Đặc trưng trong preprocess + model |

**Tổng ML Layer:** 7/8 ✅, 1 ⏳ (LSTM)

---

## 4. Detection Strategy (Hybrid Detection)

| # | Task | Trạng thái | Ghi chú / File |
|---|------|------------|----------------|
| 4.1 | Rule-based (Logstash) | ✅ | brute_force, sql_injection, xss trong pipeline.conf |
| 4.2 | Rule-based (threshold / Python) | ⏳ | Có thể mở rộng trong preprocess |
| 4.3 | ML – Random Forest | ✅ | `scripts/ml_detector.py` |
| 4.4 | ML – Isolation Forest | ✅ | `scripts/ml_detector.py` |
| 4.5 | ML – One-Class SVM | ✅ | `scripts/ml_detector.py` |
| 4.6 | ML – Deep Learning (LSTM) | ⏳ | Future work |

**Tổng Detection Strategy:** 4/6 ✅, 2 ⏳

---

## 5. Response Layer (Semi-Automated Response Framework)

| # | Task | Trạng thái | Ghi chú / File |
|---|------|------------|----------------|
| 5.1 | Alert generation | ✅ | Index ml-alerts-*; Kibana Alerting (docs); app "View Alerts" |
| 5.2 | Visualization (Kibana + app) | ✅ | Kibana Discover/Dashboard; app Timeline, thống kê |
| 5.3 | Suggest defense (rule engine) | ✅ | `scripts/defense_recommendations.py`; elasticsearch_writer ghi vào ml-alerts; app "Xem đề xuất phòng thủ" |
| 5.4 | Auto block IP | ⏳ | Placeholder `scripts/response/auto_mitigation_stub.py` |
| 5.5 | Firewall integration | ⏳ | Future |
| 5.6 | IDS integration | ⏳ | Future |

**Tổng Response Layer:** 3/6 ✅, 3 ⏳

---

## 6. Luồng & công cụ theo kiến trúc

| # | Task | Trạng thái | Ghi chú / File |
|---|------|------------|----------------|
| 6.1 | Script chạy luồng 1→5 | ✅ | `scripts/run_by_architecture.py` |
| 6.2 | Nút app "Chạy luồng theo kiến trúc (1→5)" | ✅ | run_simulation_app.py – action 14 |
| 6.3 | Config ánh xạ 5 tầng | ✅ | `config/architecture_layers.yaml` |
| 6.4 | Tài liệu kiến trúc | ✅ | `docs/ARCHITECTURE_RESEARCH.md` |
| 6.5 | Placeholder Response (SOAR) | ✅ | `scripts/response/README.md`, `auto_mitigation_stub.py` |

**Tổng Luồng & công cụ:** 5/5 ✅

---

## 7. Index Elasticsearch

| # | Task | Trạng thái | Ghi chú |
|---|------|------------|--------|
| 7.1 | test-logs-* (raw) | ✅ | Filebeat → Logstash → ES |
| 7.2 | ssh-logs-* (parsed + rule) | ✅ | Logstash index_prefix |
| 7.3 | web-logs-* (parsed + rule) | ✅ | Logstash index_prefix |
| 7.4 | ml-alerts-* (alert ML) | ✅ | elasticsearch_writer.py |
| 7.5 | Feature index (features-*) | ⏳ | Future; hiện feature trong Python |

**Tổng Index:** 4/5 ✅, 1 ⏳

---

## Tổng kết

| Tầng | Đã hoàn thành | Future / optional |
|------|----------------|-------------------|
| 1. Data Layer | 6 | 1 (network logs) |
| 2. SIEM Layer | 8 | 0 |
| 3. ML Layer | 7 | 1 (LSTM) |
| 4. Detection Strategy | 4 | 2 (threshold, DL) |
| 5. Response Layer | 3 | 3 (auto block, firewall, IDS) |
| Luồng & config | 5 | 0 |
| Index ES | 4 | 1 (feature index) |

**Kết luận:** Cấu trúc 5 tầng đã được triển khai đầy đủ theo đúng research paper. Các mục đánh dấu ⏳ là hướng mở rộng (future work), không bắt buộc cho phiên bản hiện tại.
