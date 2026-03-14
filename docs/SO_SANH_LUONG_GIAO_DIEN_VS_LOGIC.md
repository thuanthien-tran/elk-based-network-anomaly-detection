# So sánh giao diện / tính năng với logic mong muốn

**Logic bạn mô tả:**  
Tự động train dataset khi chạy → Tạo test.log rồi chạy tấn công → Model đã train chạy detection → Phát hiện và báo cáo tấn công → Đề xuất phòng thủ → Phòng thủ

---

## 1. So sánh từng bước

| Bước trong logic của bạn | Có trong app? | Thực tế hiện tại |
|---------------------------|---------------|-------------------|
| **1. Tự động train dataset khi chạy** | ❌ Không tự động | Train **không** chạy tự động khi mở app. Bạn phải chọn **Train UNIFIED** (hoặc Chuẩn bị & Train) rồi bấm **Execute**. Có thể thêm "Luồng demo đầy đủ" một nút để chạy tuần tự: chuẩn bị/train → ghi log → detection. |
| **2. Tạo test.log rồi chạy tấn công** | ✅ Có, nhưng tách bước | **Ghi log** tạo file test.log (số dòng normal + attack do bạn nhập). Đó chính là “tạo test.log + mô phỏng tấn công”. Không gộp chung với Detection trong một nút; cần chọn **Ghi log**, nhập số, Execute, sau đó mới chạy Detection. |
| **3. Model đã train chạy detection** | ✅ Có | **Run Detection** đọc log (từ ES hoặc fallback test.log) → preprocess → load **ssh_attack_model.joblib** → predict → ghi ml-alerts. Đúng với “model đã train chạy detection”. |
| **4. Phát hiện và báo cáo tấn công** | ✅ Có | Kết quả ghi vào index **ml-alerts** trong Elasticsearch. **View Alerts** mở Kibana Discover (ml-alerts) để xem báo cáo tấn công. |
| **5. Đề xuất phòng thủ** | ✅ Trong pipeline, ❌ Chưa rõ trên UI | Script **elasticsearch_writer** gắn **defense_recommendations** (từ `defense_recommendations.py`) vào từng bản ghi trước khi ghi ES. Trên Kibana, xem được trong từng document. Trong **app desktop** trước đây **không** có mục “Đề xuất phòng thủ”; đã bổ sung nút **Xem đề xuất phòng thủ** đọc kết quả detection và hiển thị đề xuất. |
| **6. Phòng thủ** | ⚠️ Chỉ đề xuất | Hệ thống **chỉ đưa ra đề xuất** (text); **không** tự động thực hiện phòng thủ (vd. block IP, đổi rule firewall). “Phòng thủ” trong app = xem và làm theo đề xuất; việc áp dụng (cấu hình fail2ban, firewall, v.v.) do người dùng thực hiện bên ngoài. |

---

## 2. Luồng thực tế để khớp với logic của bạn

Để chạy đúng trình tự bạn nghĩ, làm thủ công như sau:

1. **Train dataset (một lần đầu)**  
   Chọn **Chuẩn bị & Train** (Synthetic hoặc Russell) → Execute. Sau đó chọn **Train UNIFIED** → Execute (tạo `ssh_attack_model.joblib`).

2. **Tạo test.log và “chạy tấn công”**  
   Bấm **Ghi log** → nhập số dòng normal + attack → Execute (tạo/ghi đè test.log).

3. **Detection**  
   Chọn **Run Detection** → Execute (đọc test.log nếu ES trống → predict → ghi ml-alerts).

4. **Báo cáo tấn công**  
   Chọn **View Alerts** → Execute (mở Kibana xem ml-alerts).

5. **Đề xuất phòng thủ**  
   Trong app: chọn **Xem đề xuất phòng thủ** (sau khi đã chạy Detection). Trên Kibana: xem trường `defense_recommendations` trong từng bản ghi ml-alerts.

6. **Phòng thủ**  
   Làm theo đề xuất (cấu hình hệ thống, firewall, v.v.) bên ngoài app.

---

## 3. Đã chỉnh trong app để gần với logic của bạn

- **Workflow** trên giao diện được cập nhật theo đúng thứ tự: Train → Tạo log / mô phỏng tấn công → Detection → Báo cáo → Đề xuất phòng thủ.
- Thêm nút **Xem đề xuất phòng thủ** (Monitoring): đọc kết quả detection (predictions) và hiển thị đề xuất phòng thủ trong app.
- (Tùy chọn sau này) Có thể thêm **“Luồng demo đầy đủ”** một nút: tự chạy tuần tự train (nếu chưa có model) → ghi log → detection → mở Kibana; vẫn giữ “phòng thủ” là thao tác xem đề xuất và làm tay.

---

## 4. Tóm tắt

- **Train:** Có đủ chức năng nhưng **không tự động** khi “chạy”; cần bấm Train UNIFIED (và có thể Chuẩn bị & Train trước).
- **test.log + tấn công:** Có (Ghi log); đúng ý “tạo test.log rồi chạy tấn công” (mô phỏng).
- **Detection bằng model đã train:** Có (Run Detection).
- **Phát hiện và báo cáo:** Có (ml-alerts + View Alerts).
- **Đề xuất phòng thủ:** Có trong pipeline và trong ES; app đã có nút **Xem đề xuất phòng thủ**.
- **Phòng thủ:** Chỉ ở mức đề xuất; không có bước “tự động phòng thủ” trong app.

Sau khi chỉnh workflow text và thêm nút **Xem đề xuất phòng thủ**, giao diện phản ánh đúng logic bạn mô tả (trừ bước “tự động train khi chạy” và “tự động thực hiện phòng thủ”).
