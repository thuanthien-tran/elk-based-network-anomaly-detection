# 🛡️ ELKShield: Hệ Thống Giám Sát An Ninh Mạng Dựa Trên ELK Stack và Machine Learning

## 📋 Thông Tin Đồ Án

**Đề tài:** Xây dựng hệ thống giám sát an ninh mạng dựa trên ELK Stack và Machine Learning  
**Sinh viên:** [Tên sinh viên]  
**Lớp:** [Lớp]  
**Môn học:** An toàn mạng  
**Giảng viên hướng dẫn:** [Tên giảng viên]

---

## 🚀 QUICK START

**Xem hướng dẫn đầy đủ**: [HUONG_DAN_CHAY_DU_AN.md](HUONG_DAN_CHAY_DU_AN.md)

### Setup Nhanh (3 bước):

```cmd
# 1. Cài dependencies
python -m pip install -r requirements.txt

# 2. Start ELK Stack
cd docker
docker-compose up -d

# 3. Chạy Filebeat
cd ..\config\filebeat
filebeat.exe -c filebeat-test-simple.yml -e
```

Xem chi tiết trong file **HUONG_DAN_CHAY_DU_AN.md**.

---

## 🎯 Mục Tiêu Đồ Án

### Mục tiêu chính
Xây dựng một hệ thống giám sát an ninh mạng thời gian gần thực (near real-time) có khả năng:

- ✅ **Thu thập log** từ nhiều nguồn khác nhau (SSH, Web Server, Firewall, System logs)
- ✅ **Phân tích và trực quan hóa** log thông qua Kibana Dashboard
- ✅ **Phát hiện tấn công** bằng rule-based detection
- ✅ **Nâng cấp bằng Machine Learning** để phát hiện bất thường và tấn công mới

### Mục tiêu phụ
- So sánh hiệu quả giữa rule-based và ML-based detection
- Đánh giá độ chính xác của các mô hình ML
- Xây dựng hệ thống cảnh báo tự động

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────┐
│   Data Sources  │
│  ┌───────────┐  │
│  │ SSH Logs  │  │
│  │ Web Logs  │  │
│  │ Firewall  │  │
│  │ System    │  │
│  └───────────┘  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Beats Layer    │
│  ┌───────────┐  │
│  │ Filebeat  │  │
│  │ Winlogbeat│  │
│  └───────────┘  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Logstash      │
│  (Parse/Filter) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Elasticsearch   │
│  (Storage)      │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│ Kibana  │ │ ML Module    │
│ Dashboard│ │ (Python)     │
└─────────┘ └──────────────┘
```

### Các thành phần chính

| Thành phần | Vai trò | Công nghệ |
|------------|---------|-----------|
| **Beats** | Thu thập log từ các nguồn | Filebeat, Winlogbeat |
| **Logstash** | Xử lý, parse, filter log | Logstash Pipeline |
| **Elasticsearch** | Lưu trữ & tìm kiếm | Elasticsearch 8.x |
| **Kibana** | Dashboard & Visualization | Kibana 8.x |
| **ML Module** | Phát hiện bất thường | Python (scikit-learn, pandas) |

---

## 📅 Roadmap Triển Khai

### **Giai đoạn 1: Nghiên cứu nền tảng** (Tuần 1-2)

#### 1.1 Nghiên cứu ELK Stack
- [ ] Tìm hiểu về Elasticsearch: indexing, querying, mapping
- [ ] Nghiên cứu Logstash: pipeline, filters (grok, mutate, date)
- [ ] Học Kibana: visualization, dashboard, Discover
- [ ] Tìm hiểu Beats: Filebeat, Winlogbeat configuration

**Tài liệu tham khảo:**
- Elasticsearch Official Documentation
- Logstash Configuration Guide
- Kibana Visualization Guide

#### 1.2 Nghiên cứu các loại tấn công phổ biến
- [ ] **Brute Force Attack**: SSH brute force, web login brute force
- [ ] **DDoS Attack**: SYN flood, UDP flood, HTTP flood
- [ ] **Port Scanning**: Nmap scan patterns
- [ ] **SQL Injection**: Web application attacks
- [ ] **Web Attack**: XSS, Path traversal

**Pattern cần nhận diện:**
- Multiple failed login attempts từ cùng một IP
- Unusual traffic spikes
- Suspicious port scanning patterns
- SQL injection patterns trong web logs

#### 1.3 Nghiên cứu Machine Learning trong IDS
- [ ] **Supervised Learning**: Random Forest, XGBoost, Neural Networks
- [ ] **Unsupervised Learning**: Isolation Forest, One-Class SVM, K-Means
- [ ] **Anomaly Detection**: Statistical methods, ML-based
- [ ] **Dataset nghiên cứu**:
  - NSL-KDD Dataset
  - CICIDS2017 Dataset
  - UNSW-NB15 Dataset

**Kết quả mong đợi:**
- Báo cáo tổng hợp về ELK Stack
- Phân tích các loại tấn công và signature
- So sánh các phương pháp ML cho IDS

---

### **Giai đoạn 2: Xây dựng môi trường Lab** (Tuần 3)

#### 2.1 Thiết lập môi trường ảo hóa

**Cấu hình đề xuất:**

| VM | OS | RAM | Vai trò |
|----|----|-----|---------|
| **ELK Server** | Ubuntu 22.04 LTS | 4GB+ | Chạy ELK Stack |
| **Attacker** | Kali Linux 2024 | 2GB | Mô phỏng tấn công |
| **Victim** | Ubuntu Server 22.04 | 2GB | Web Server, SSH Server |

**Công cụ:**
- VMware Workstation / VirtualBox
- Docker & Docker Compose (nếu máy yếu)

#### 2.2 Cấu hình mạng
- [ ] Thiết lập NAT network cho các VM
- [ ] Cấu hình static IP cho ELK Server
- [ ] Test kết nối giữa các VM

**Kết quả mong đợi:**
- Môi trường lab hoàn chỉnh
- Tất cả VM có thể giao tiếp với nhau

---

### **Giai đoạn 3: Triển khai ELK Stack** (Tuần 4-5)

#### 3.1 Cài đặt Elasticsearch
- [ ] Cài đặt Elasticsearch 8.x
- [ ] Cấu hình cluster (single-node cho lab)
- [ ] Tạo index template cho logs
- [ ] Test lưu trữ và query

**Index cần tạo:**
- `ssh-logs-*`
- `web-logs-*`
- `firewall-logs-*`
- `system-logs-*`

#### 3.2 Cài đặt Logstash
- [ ] Cài đặt Logstash 8.x
- [ ] Viết pipeline config cho SSH logs
- [ ] Viết pipeline config cho Apache/Nginx logs
- [ ] Sử dụng Grok patterns để parse log
- [ ] Thêm filters: mutate, date, geoip

**Pipeline cần xây dựng:**
```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse SSH logs
  if [fields][log_type] == "ssh" {
    grok { ... }
  }
  
  # Parse Web logs
  if [fields][log_type] == "web" {
    grok { ... }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "%{[fields][log_type]}-logs-%{+YYYY.MM.dd}"
  }
}
```

#### 3.3 Cài đặt Kibana
- [ ] Cài đặt Kibana 8.x
- [ ] Kết nối với Elasticsearch
- [ ] Tạo Index Patterns
- [ ] Xây dựng Dashboard:
  - **Top IP truy cập**
  - **Failed login attempts**
  - **Tần suất truy cập theo thời gian**
  - **Geographic map của IPs**
  - **Error rate**

#### 3.4 Thu thập log với Beats
- [ ] Cài đặt Filebeat trên Victim VM
- [ ] Cấu hình thu thập:
  - `/var/log/auth.log` (SSH)
  - `/var/log/apache2/access.log` (Web)
  - `/var/log/syslog` (System)
- [ ] Test log flow: Beats → Logstash → Elasticsearch → Kibana

**Kết quả mong đợi:**
- ✅ Dashboard Kibana hiển thị log real-time
- ✅ Log được parse đúng format
- ✅ Có thể query và filter log

---

### **Giai đoạn 4: Mô phỏng tấn công** (Tuần 6)

#### 4.1 Thực hiện các cuộc tấn công

| Loại Attack | Công cụ | Mục đích |
|-------------|---------|----------|
| **Brute Force SSH** | Hydra, Medusa | Test phát hiện failed login |
| **Port Scanning** | Nmap | Test phát hiện scan pattern |
| **DoS Attack** | hping3, Slowloris | Test phát hiện traffic spike |
| **Web Attack** | sqlmap, Nikto | Test phát hiện web attack |
| **DDoS Simulation** | Multiple tools | Test phát hiện distributed attack |

#### 4.2 Phân tích log trong Kibana
- [ ] Xác định pattern của từng loại attack
- [ ] Tạo visualizations cho các attack
- [ ] Ghi nhận các signature đặc trưng

**Kết quả mong đợi:**
- ✅ Log ghi nhận đầy đủ các attack
- ✅ Có thể phân biệt các loại attack trong Kibana
- ✅ Hiểu rõ pattern của từng loại attack

---

### **Giai đoạn 5: Tích hợp Machine Learning** (Tuần 7-8)

#### 5.1 Chuẩn bị dữ liệu
- [ ] Export log từ Elasticsearch sang CSV/JSON
- [ ] Tiền xử lý dữ liệu:
  - Encode IP addresses
  - Chuẩn hóa dữ liệu
  - Handle missing values
- [ ] Feature Engineering:
  - Request per minute per IP
  - Failed login count per IP
  - Session duration
  - Geographic features
  - Time-based features (hour, day of week)

**Script Python cần viết:**
- `data_extraction.py`: Export từ Elasticsearch
- `data_preprocessing.py`: Clean và transform data
- `feature_engineering.py`: Tạo features

#### 5.2 Áp dụng mô hình ML

**Hướng 1: Unsupervised Learning (Đề xuất)**

- [ ] **Isolation Forest**
  - Phát hiện outliers/anomalies
  - Không cần labeled data
  
- [ ] **One-Class SVM**
  - Học pattern bình thường
  - Phát hiện deviations
  
- [ ] **K-Means Clustering**
  - Phân cụm traffic
  - Phát hiện cluster bất thường

**Hướng 2: Supervised Learning (Nâng cao)**

- [ ] **Random Forest**
  - Train với labeled data
  - Feature importance analysis
  
- [ ] **XGBoost**
  - High performance
  - Better accuracy
  
- [ ] **Neural Network**
  - Deep learning approach
  - Auto-encoder cho anomaly detection

#### 5.3 Workflow tích hợp
```
ELK Stack → Export Log → Python ML Module → 
Anomaly Score → Write back to Elasticsearch → 
Kibana Alert Dashboard
```

**Script cần phát triển:**
- `ml_detector.py`: Main ML detection script
- `anomaly_scorer.py`: Tính anomaly score
- `elasticsearch_writer.py`: Ghi kết quả về ES

**Kết quả mong đợi:**
- ✅ ML model có thể phát hiện anomalies
- ✅ Kết quả được tích hợp vào Elasticsearch
- ✅ Có thể so sánh với rule-based detection

---

### **Giai đoạn 6: Xây dựng Dashboard cảnh báo thông minh** (Tuần 8)

#### 6.1 Tạo ML Alerts Index
- [ ] Tạo index `ml-alerts-*` trong Elasticsearch
- [ ] Định nghĩa mapping cho alerts

#### 6.2 Dashboard trong Kibana
- [ ] **Attack Timeline**: Timeline của các attack được phát hiện
- [ ] **Anomaly Score Chart**: Biểu đồ anomaly score theo thời gian
- [ ] **Top Suspicious IPs**: Danh sách IP đáng nghi nhất
- [ ] **Heatmap**: Heatmap của traffic patterns
- [ ] **Comparison View**: So sánh Rule-based vs ML-based

**Kết quả mong đợi:**
- ✅ Dashboard trực quan và dễ hiểu
- ✅ Cảnh báo real-time
- ✅ Có thể drill-down vào chi tiết

---

### **Giai đoạn 7: Đánh giá hiệu quả hệ thống** (Tuần 9)

#### 7.1 Các tiêu chí đánh giá

| Chỉ số | Công thức | Ý nghĩa |
|--------|-----------|---------|
| **Accuracy** | (TP + TN) / (TP + TN + FP + FN) | Độ chính xác tổng thể |
| **Precision** | TP / (TP + FP) | Tỷ lệ đúng trong dự đoán attack |
| **Recall** | TP / (TP + FN) | Khả năng phát hiện attack |
| **F1-Score** | 2 × (Precision × Recall) / (Precision + Recall) | Cân bằng Precision & Recall |
| **False Positive Rate** | FP / (FP + TN) | Tỷ lệ cảnh báo sai |

#### 7.2 So sánh phương pháp
- [ ] So sánh **Rule-based** vs **ML-based**:
  - Số lượng attack phát hiện được
  - False positive rate
  - Thời gian phát hiện
  - Khả năng phát hiện attack mới

#### 7.3 Test với dataset chuẩn
- [ ] Test với NSL-KDD dataset
- [ ] Test với CICIDS2017 dataset
- [ ] So sánh kết quả với các nghiên cứu khác

**Kết quả mong đợi:**
- ✅ Bảng so sánh chi tiết
- ✅ Biểu đồ so sánh hiệu quả
- ✅ Phân tích ưu/nhược điểm

---

### **Giai đoạn 8: Viết báo cáo và chuẩn bị demo** (Tuần 10)

#### 8.1 Cấu trúc báo cáo
1. **Giới thiệu**
   - Đặt vấn đề
   - Mục tiêu nghiên cứu
   - Phạm vi nghiên cứu

2. **Cơ sở lý thuyết**
   - ELK Stack
   - Machine Learning trong IDS
   - Các loại tấn công mạng

3. **Thiết kế hệ thống**
   - Kiến trúc tổng thể
   - Thiết kế các module
   - Flow xử lý dữ liệu

4. **Triển khai thực nghiệm**
   - Môi trường thực nghiệm
   - Cấu hình hệ thống
   - Quá trình triển khai

5. **Kết quả và đánh giá**
   - Kết quả thực nghiệm
   - So sánh phương pháp
   - Phân tích kết quả

6. **Kết luận và hướng phát triển**
   - Kết luận
   - Hạn chế
   - Hướng phát triển

#### 8.2 Demo
- [ ] Chuẩn bị demo live
- [ ] Video demo (backup)
- [ ] Slides presentation

---

## 🚀 Hướng Phát Triển Nâng Cao

### Các tính năng nâng cao đã triển khai ✅

1. **ML Evaluator với Visualizations**
   - ROC Curve plots
   - Precision-Recall curves
   - Confusion matrix visualization
   - Feature importance ranking
   - Comprehensive metrics reports

2. **Method Comparison Tool**
   - So sánh Rule-based vs ML-based
   - Metrics comparison charts
   - Error rates analysis
   - Detailed comparison reports

3. **Performance Benchmarking**
   - Data extraction speed
   - Preprocessing throughput
   - ML training/prediction time
   - Elasticsearch indexing performance

4. **False Positive Analyzer**
   - FP analysis by IP
   - FP analysis by attack type
   - Score distribution comparison
   - Detailed FP reports

### Các tính năng có thể phát triển thêm

1. **Tích hợp Suricata IDS**
   - Suricata → Logstash → Elasticsearch
   - Signature-based detection

2. **Tích hợp Wazuh**
   - Wazuh agent trên các server
   - Compliance monitoring

3. **Web UI riêng**
   - Flask/FastAPI backend
   - React/Vue frontend
   - Custom dashboard

4. **Cloud Deployment**
   - Deploy trên AWS/GCP/Azure
   - Elastic Cloud Service

5. **Real-time Alerting**
   - Email notifications
   - Slack/Telegram integration
   - Webhook support

---

## 📊 Timeline Tổng Quan

| Tuần | Giai đoạn | Nội dung chính | Deliverables |
|------|-----------|----------------|--------------|
| **1-2** | Nghiên cứu | ELK Stack, Attacks, ML | Báo cáo nghiên cứu |
| **3** | Setup Lab | VM, Network config | Môi trường lab |
| **4-5** | Triển khai ELK | Install & config ELK | Dashboard cơ bản |
| **6** | Mô phỏng attack | Thực hiện attacks | Log analysis |
| **7-8** | ML Integration | ML models, Integration | ML detection |
| **8** | Dashboard | Alert dashboard | Dashboard hoàn chỉnh |
| **9** | Đánh giá | Testing, Evaluation | Báo cáo đánh giá |
| **10** | Báo cáo | Viết báo cáo, Demo | Báo cáo + Demo |

---

## 🎓 Chiến Lược Đạt Điểm Cao

### ✅ Checklist để đạt điểm cao:

- [x] **Có thực nghiệm thật**: Không chỉ lý thuyết, phải có hệ thống chạy được
- [x] **Có số liệu so sánh**: So sánh rule-based vs ML-based với số liệu cụ thể
- [x] **Có biểu đồ**: Visualization đẹp, dễ hiểu
- [x] **Có ML thật sự chạy**: Không chỉ demo, phải có model train và test
- [x] **Có đánh giá ưu/nhược điểm**: Phân tích khách quan
- [x] **Code quality**: Code sạch, có comment, có documentation
- [x] **Presentation tốt**: Slides đẹp, demo mượt

### 📈 Điểm cộng:

- ⭐ Sử dụng dataset chuẩn (NSL-KDD, CICIDS2017)
- ⭐ So sánh nhiều mô hình ML
- ⭐ Có visualization đẹp
- ⭐ Code được đăng trên GitHub
- ⭐ Có video demo

---

## 📁 Cấu Trúc Thư Mục Đề Xuất

```
ELKShield/
├── README.md
├── docs/
│   ├── research/
│   ├── design/
│   └── evaluation/
├── config/
│   ├── elasticsearch/
│   ├── logstash/
│   ├── kibana/
│   └── filebeat/
├── scripts/
│   ├── data_extraction.py
│   ├── data_preprocessing.py
│   ├── ml_detector.py
│   └── anomaly_scorer.py
├── ml_models/
│   ├── isolation_forest.pkl
│   ├── one_class_svm.pkl
│   └── random_forest.pkl
├── docker/
│   └── docker-compose.yml
└── reports/
    └── final_report.md
```

---

## 🔗 Tài Liệu Tham Khảo

### Tài liệu chính thức
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Logstash Documentation](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Kibana Documentation](https://www.elastic.co/guide/en/kibana/current/index.html)

### Dataset
- [NSL-KDD Dataset](https://www.unb.ca/cic/datasets/nsl.html)
- [CICIDS2017 Dataset](https://www.unb.ca/cic/datasets/ids-2017.html)
- [UNSW-NB15 Dataset](https://www.unsw.adfa.edu.au/unsw-canberra-cyber/cybersecurity/ADFA-NB15-Datasets/)

### Papers
- "A Survey of Intrusion Detection Systems" - Various authors
- "Machine Learning for Network Intrusion Detection" - Various authors

---

## 📝 Ghi Chú

- Roadmap này có thể điều chỉnh tùy theo tiến độ thực tế
- Ưu tiên hoàn thành các giai đoạn cốt lõi trước
- Luôn backup code và config
- Document mọi thay đổi và quyết định

---

**Chúc bạn thành công với đồ án! 🎉**
