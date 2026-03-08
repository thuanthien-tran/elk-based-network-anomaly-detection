# Kiểm tra hoàn thành – Kiến trúc SIEM + ML Hybrid

Tài liệu này xác nhận các task đã triển khai theo phương án và đánh giá đã thống nhất.

---

## 1. Phương án tổng thể

| Đánh giá | Trạng thái | Ghi chú |
|----------|------------|--------|
| Gộp Synthetic + Russell + Kaggle để train **một** Random Forest | ✅ Hoàn thành | `merge_training_datasets.py` → `unified_ssh_dataset.csv`; `train_model.py` train RF |
| ELK logs **chỉ** dùng cho realtime detection với model đó | ✅ Hoàn thành | `run_pipeline_detection.py` load `ssh_attack_model.joblib`, không train lại |
| Kiến trúc: training datasets → RF → model → ELK logs → feature extract → ML detect → ES → Kibana | ✅ Hoàn thành | Khớp với luồng offline + online đã implement |

---

## 2. Chuẩn hóa schema và nhãn

| Task | Trạng thái | Chi tiết |
|------|------------|----------|
| Chuẩn hóa schema khi gộp | ✅ | `merge_training_datasets.py`: bỏ cột `host`, thêm `geoip_country`/`geoip_city` nếu thiếu; cột chuẩn `STANDARD_COLS` |
| Thống nhất nhãn `is_attack` | ✅ | Normalize `is_attack` sang bool; dùng chung cho train và detection |

---

## 3. Định dạng model

| Task | Trạng thái | Chi tiết |
|------|------------|----------|
| Giữ `.joblib` | ✅ | Model lưu: `data/models/ssh_attack_model.joblib` |
| Tên file model thống nhất | ✅ | `ssh_attack_model.joblib` dùng trong train và detection |

---

## 4. Kiến trúc từng phần

| Phần | Trạng thái | Cách kiểm tra |
|------|------------|----------------|
| **Offline training + Online detection** | ✅ | DEMO [6]→[5] train; [6]→[1] detection |
| **TRAINING:** gộp 3 dataset → unified → train → model.joblib | ✅ | `train_model.py` (gọi merge → clean → train RF → save) |
| **DETECTION:** test.log → ELK → feature → model → ml-alerts → Kibana | ✅ | `run_pipeline_detection.py` dùng đúng model và index `ml-alerts` |
| **Cấu trúc folder** | ✅ | `data/training/`, `data/models/ssh_attack_model.joblib` |

---

## 5. File và script liên quan

| Thành phần | Đường dẫn / Lệnh |
|------------|-------------------|
| Gộp dataset | `scripts/merge_training_datasets.py` → `data/training/unified_ssh_dataset.csv` |
| Train unified | `scripts/train_model.py` → `data/models/ssh_attack_model.joblib` |
| Detection online | `scripts/run_pipeline_detection.py` (load `ssh_attack_model.joblib`, ghi ml-alerts) |
| DEMO menu | [6] Chọn dataset → [5] Train unified; [1] Detection online |

---

## 6. Câu demo (khi thuyết trình)

> *"The system uses historical SSH datasets to train a machine learning model offline. The trained model is then deployed into a real-time ELK-based SIEM pipeline to detect attacks from live logs."*

Câu này **đúng** với kiến trúc đã triển khai và có thể dùng khi demo đồ án.

---

## 7. Tóm tắt

- **Offline:** Synthetic + Russell Mitchell + Kaggle → merge → clean → feature (preprocess) → train Random Forest → `ssh_attack_model.joblib`.
- **Online:** test.log → Filebeat → Logstash → Elasticsearch → extract → preprocess → load `ssh_attack_model.joblib` → predict → ghi ml-alerts → Kibana.

Tất cả task trong phương án đánh giá đã được triển khai và kiểm tra xong.
