# Kiểm tra logic train và sử dụng data trong thư mục data/

## 1. Các nguồn data trong `data/` được dùng cho train

| Nguồn | Đường dẫn / file | Cách đưa vào train | Ghi chú |
|-------|------------------|--------------------|--------|
| **Synthetic** | `data/raw/logs.csv` → preprocess → `data/processed/logs.csv` | Merge → unified → train UNIFIED | Sinh bởi `generate_synthetic_logs.py` hoặc từ ELK extract. |
| **Russell Mitchell** | `data/russellmitchell/gather/.../auth.log` → convert → `data/raw/russellmitchell_auth.csv` → preprocess → `data/processed/russellmitchell_processed.csv` | Merge → unified → train UNIFIED | Script: `russellmitchell_auth_to_csv.py` + `data_preprocessing.py`. |
| **Kaggle SSH** | `data/ssh_anomaly_dataset.csv` → (convert) → preprocess → `data/processed/pipeline_ssh_processed.csv` | Merge → unified → train UNIFIED | Script: `run_pipeline_ssh.py --kaggle` hoặc Kaggle + preprocess. |
| **Custom (tệp CSV)** | Đường dẫn tùy chọn → preprocess → `data/processed/custom_processed.csv` | Merge → unified → train UNIFIED | Từ mục "Train từ CSV (Kaggle / tệp)" chọn Tệp. **Đã bổ sung:** merge gộp luôn `custom_processed.csv` nếu tồn tại. |

Tất cả file trên đều nằm trong thư mục project `data/` (raw, processed, training).

---

## 2. Đã tối ưu / đã sửa

### 2.1 Gộp đủ 4 nguồn khi train UNIFIED

- **Trước:** `merge_training_datasets.py` chỉ gộp 3 file cố định: `logs.csv`, `russellmitchell_processed.csv`, `pipeline_ssh_processed.csv`. File `custom_processed.csv` (từ "Train từ CSV" với tệp tùy chọn) **không** được đưa vào unified.
- **Sau:** Thêm nguồn thứ 4 **Custom** → `data/processed/custom_processed.csv`. Nếu file tồn tại thì được gộp vào unified; không tồn tại thì bỏ qua (giữ hành vi cũ cho 3 nguồn kia).
- **Cách dùng:** Chạy Train UNIFIED như bình thường. Merge tự đọc cả 4 file (Synthetic, Russell, Kaggle, Custom); file nào có thì gộp.

### 2.2 Cập nhật mô tả lỗi trong `train_model.py`

- Khi merge thất bại (không có file nào), thông báo in rõ cần ít nhất một trong bốn file, bao gồm `custom_processed.csv`.

---

## 3. Luồng train và dùng data (tóm tắt)

```
data/raw/logs.csv                    → preprocess → data/processed/logs.csv
data/russellmitchell/.../auth.log    → convert → raw/russellmitchell_auth.csv → preprocess → russellmitchell_processed.csv
data/ssh_anomaly_dataset.csv         → (kaggle convert) → preprocess → pipeline_ssh_processed.csv
<đường dẫn CSV tùy chọn>             → preprocess → custom_processed.csv
        ↓
merge_training_datasets.py (đọc mọi file tồn tại trong danh sách trên)
        ↓
data/training/unified_ssh_dataset.csv
        ↓
train_model.py (clean + train RF)
        ↓
data/models/ssh_attack_model.joblib
```

---

## 4. Data trong `data/` chưa được dùng cho train SSH

| Thành phần | Lý do / ghi chú |
|------------|------------------|
| **data/dataset1/** (Twente: auth.log.anon, kippo.log.anon) | README/analyze nhắc dùng cho SSH pipeline, nhưng **chưa có script** convert dataset1 → CSV chuẩn và chưa có bước preprocess → merge. Muốn dùng: cần script convert (vd. twente_auth_to_csv.py) và đưa output vào preprocess rồi thêm vào merge (hoặc dùng như Custom). |
| **data/apache-http-logs-master/** | Dùng cho **pipeline web** (`run_pipeline_web.py`), không phải train SSH. Model web lưu riêng (vd. `web_attack_model.joblib`). |
| **data/caudit-master/** | Được analyze_datasets liệt kê; chưa thấy pipeline nào đọc. Có thể bổ sung tương tự dataset1 nếu cần. |
| **Các file .xlsx / .md trong data/** | Tài liệu / bảng tính; không phải input train. |

---

## 5. Kết luận

- **Đã dùng hết** cho train SSH (model chính): mọi CSV đã preprocess trong `data/processed/` mà pipeline tạo ra (Synthetic, Russell, Kaggle, Custom) đều được merge và train khi chạy Train UNIFIED.
- **Đã tối ưu:** Gộp thêm `custom_processed.csv` vào merge, không bỏ sót dữ liệu từ "Train từ CSV" với tệp tùy chọn.
- **Chưa dùng:** dataset1 (Twente), caudit-master và các nguồn log thô khác chưa có bước convert/preprocess vào `data/processed/`; nếu cần dùng thì phải thêm script tương ứng và (tùy chọn) thêm vào merge hoặc dùng như Custom.
