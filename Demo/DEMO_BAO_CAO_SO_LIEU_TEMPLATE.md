# DEMO BÁO CÁO SỐ LIỆU (TEMPLATE) — ELKShield Unified Security Platform

## Mục đích
Template này tạo sẵn các bảng/ô trống để bạn chạy demo của dự án, rồi điền số liệu thực tế vào.

## 1) Thông tin demo

| Trường | Giá trị (điền tay) |
|---|---|
| Ngày giờ chạy demo | `__________` |
| Máy/OS | `__________` |
| Python version | `__________` |
| Elasticsearch status | `OK / FAIL` |
| Filebeat status | `OK / FAIL` |
| Kibana URL | `__________` |

## 2) Train model (ghi theo thao tác bạn đã làm)

### 2.1) Train Global Model (UNIFIED) — nếu bạn bấm nút này

| Trường | Giá trị (điền tay) |
|---|---|
| Nút đã bấm | `Train Global Model / UNIFIED` |
| Dataset đã dùng | `Synthetic + Russell Mitchell + Kaggle` (hoặc ghi khác) |
| Dataset output CSV | `data/training/unified_ssh_dataset.csv` (hoặc file khác: `__________`) |
| Model output file | `data/models/ssh_attack_model.joblib` (hoặc file khác: `__________`) |
| Model metrics (nếu có) | `Accuracy / Precision / Recall / F1 = __________` |
| Confusion matrix (Attack=Positive) | `TP=__, FP=__, FN=__, TN=__` |

### 2.2) Train Scenario Model (Kaggle / Custom) — nếu bạn bấm nút này

| Trường | Giá trị (điền tay) |
|---|---|
| Nguồn Scenario dataset | `Kaggle` hoặc `Custom` |
| Đường dẫn CSV custom (nếu Custom) | `__________` |
| Output model file (scenario) | `__________` |
| Output CSV trung gian (nếu có) | `__________` |
| Ghi chú | `__________` |

## 3) Chạy demo tích hợp (Start Security Workflow)

### 3.1) Dòng chạy pipeline (ghi trạng thái “OK/FAIL”)

| Bước | Trạng thái | Ghi chú (nếu có lỗi) |
|---|---|---|
| 1. Check ELK | `OK/FAIL` | `__________` |
| 2. Load Model | `OK/FAIL` | Model: `__________` |
| 3. Collect Logs | `OK/FAIL` | Lấy từ ES hay fallback file: `__________` |
| 4. Feature Extraction | `OK/FAIL` | `__________` |
| 5. ML Detection | `OK/FAIL` | Output CSV: `data/predictions.csv` hoặc `__________` |
| 6. Write Alert ES | `OK/FAIL` | Index: `ml-alerts` (hoặc `__________`) |
| 7. Suggest Defense | `OK/FAIL` | `__________` |
| 8. Dashboard Update | `OK/FAIL` | Kibana: `__________` |

### 3.2) Số liệu tổng hợp (điền sau khi demo chạy)

| Trường | Giá trị (điền tay) |
|---|---|
| Logs processed | `__________` |
| Attacks detected (Attack count) | `__________` |
| Top attacker IP | `__________` |
| Accuracy | `__________%` |
| Precision | `__________` |
| Recall | `__________` |
| F1 | `__________` |
| Log ingestion rate (last 60 min) | `__________ logs/min` |
| Alert rate (last 60 min) | `__________ alerts/hour` |
| Model version | `__________` |
| Dataset version | `__________` |

### 3.3) Confusion Matrix (Attack = Positive)

|  | Pred Attack | Pred Normal |
|---|---:|---:|
| Actual Attack | `TP = ________` | `FN = ________` |
| Actual Normal | `FP = ________` | `TN = ________` |

## 4) Timeline Attacks (Last 24 hours)
Bạn điền số lượng tấn công theo giờ (0..23) lấy từ UI/biểu đồ timeline (tương ứng “Last 24 hours”).

| Hour | # Attacks |
|---|---:|
| 00 | `______` |
| 01 | `______` |
| 02 | `______` |
| 03 | `______` |
| 04 | `______` |
| 05 | `______` |
| 06 | `______` |
| 07 | `______` |
| 08 | `______` |
| 09 | `______` |
| 10 | `______` |
| 11 | `______` |
| 12 | `______` |
| 13 | `______` |
| 14 | `______` |
| 15 | `______` |
| 16 | `______` |
| 17 | `______` |
| 18 | `______` |
| 19 | `______` |
| 20 | `______` |
| 21 | `______` |
| 22 | `______` |
| 23 | `______` |

## 5) Defense strategy evidence (SOAR / Rule suggestion)

| # | Rule/Condition | Gợi ý phòng thủ (ghi đúng UI/field) | Kết quả (OK/FAIL) |
|---:|---|---|---|
| 1 | `IF brute force ...` (ví dụ) | `__________` | `OK/FAIL` |
| 2 | `__________` | `__________` | `OK/FAIL` |
| 3 | `__________` | `__________` | `OK/FAIL` |

## 6) Artifact checklist (đính kèm để hội đồng chấm)
- Ảnh chụp `STATUS BAR` có các metrics: ingestion rate/alert rate/model version/dataset version.
- Ảnh chụp `Attack Timeline` (Last 24 hours).
- Ảnh chụp Kibana `Discover` / index `ml-alerts-*` có records.
- Trích đoạn 5-10 dòng từ `data/predictions.csv` (nếu nộp file).
- Ghi chú nếu ES writer thất bại (error message + cách khắc phục).

