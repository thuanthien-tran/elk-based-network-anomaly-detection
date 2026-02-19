# ELKShield - Hệ Thống Giám Sát An Ninh Mạng

**Đề tài:** Xây dựng hệ thống giám sát an ninh mạng dựa trên ELK Stack và Machine Learning  
**GitHub:** https://github.com/thuanthien-tran/elk-based-network-anomaly-detection

---

## MỤC LỤC

1. [Tổng Quan Dự Án](#1-tổng-quan-dự-án)
2. [Kiến Trúc Hệ Thống](#2-kiến-trúc-hệ-thống)
3. [Hướng Dẫn Cài Đặt](#3-hướng-dẫn-cài-đặt)
4. [Hướng Dẫn Sử Dụng](#4-hướng-dẫn-sử-dụng)
5. [Tổng Hợp Code](#5-tổng-hợp-code)
6. [Đánh Giá Dự Án](#6-đánh-giá-dự-án)
7. [Đẩy Lên GitHub](#7-đẩy-lên-github)

---

## 1. TỔNG QUAN DỰ ÁN

### Mục Tiêu
Xây dựng một hệ thống giám sát an ninh mạng thời gian gần thực (near real-time) có khả năng:
- ✅ Thu thập log từ nhiều nguồn (SSH, Web Server, Firewall, System logs)
- ✅ Phân tích và trực quan hóa log thông qua Kibana Dashboard
- ✅ Phát hiện tấn công bằng rule-based detection
- ✅ Nâng cấp bằng Machine Learning để phát hiện bất thường và tấn công mới

### Kiến Trúc
```
Filebeat → Logstash → Elasticsearch → Python ML → Elasticsearch → Kibana
```

### Công Nghệ Sử Dụng
- **ELK Stack**: Elasticsearch 8.11.0, Logstash 8.11.0, Kibana 8.11.0
- **Beats**: Filebeat 9.3.0
- **Machine Learning**: Python 3.8+, scikit-learn, pandas, numpy
- **Containerization**: Docker, Docker Compose

---

## 2. KIẾN TRÚC HỆ THỐNG

### 2.1 Docker Compose

File: `docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elk-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    ports:
      - "9200:9200"
      - "9300:9300"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - elk-network
    mem_limit: 4g
    mem_reservation: 2g
    cpus: 2.0

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: elk-logstash
    volumes:
      - ../config/logstash/pipeline.conf:/usr/share/logstash/pipeline/pipeline.conf:ro
      - logstash_data:/usr/share/logstash/data
    ports:
      - "5044:5044"
      - "9600:9600"
    environment:
      - "LS_JAVA_OPTS=-Xmx1g -Xms1g"
    depends_on:
      - elasticsearch
    networks:
      - elk-network
    mem_limit: 2g
    mem_reservation: 1g
    cpus: 1.0

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: elk-kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - SERVER_HOST=0.0.0.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    networks:
      - elk-network
    mem_limit: 1g
    mem_reservation: 512m
    cpus: 0.5

volumes:
  elasticsearch_data:
    driver: local
  logstash_data:
    driver: local

networks:
  elk-network:
    driver: bridge
```

### 2.2 Filebeat Config

File: `config/filebeat/filebeat-test-simple.yml`

```yaml
filebeat.inputs:
  - type: filestream
    id: test-logs-simple
    enabled: true
    paths:
      - C:/Users/thuan/Desktop/test.log

output.logstash:
  hosts: ["127.0.0.1:5044"]
```

---

## 3. HƯỚNG DẪN CÀI ĐẶT

### 3.1 Yêu Cầu Hệ Thống

**Phần Cứng:**
- RAM: Tối thiểu 8GB (khuyến nghị 16GB)
- CPU: 4 cores trở lên
- Disk: 50GB+ free space
- OS: Windows 10/11 hoặc Ubuntu 22.04+

**Phần Mềm:**
- Docker Desktop (Windows) hoặc Docker Engine (Linux)
- Python 3.8+
- Git (optional)

### 3.2 Setup Ban Đầu

**Chạy script tự động:**
```cmd
setup.bat
```

Hoặc setup manual:
```cmd
REM Tạo thư mục
mkdir data\raw
mkdir data\processed
mkdir ml_models
mkdir reports

REM Cài Python dependencies
python -m pip install -r requirements.txt
```

### 3.3 Start ELK Stack

```cmd
cd docker
docker-compose up -d
```

**Kiểm tra:**
```cmd
docker ps
curl http://127.0.0.1:9200
```

Mở Kibana: http://localhost:5601

### 3.4 Chạy Filebeat

```cmd
cd config\filebeat
filebeat.exe -c filebeat-test-simple.yml -e
```

---

## 4. HƯỚNG DẪN SỬ DỤNG

### 4.1 Workflow Hoàn Chỉnh

#### Bước 1: Start ELK Stack
```cmd
cd docker
docker-compose up -d
```

#### Bước 2: Thu Thập Logs
```cmd
REM Tạo test logs
cd config\filebeat
powershell -ExecutionPolicy Bypass -File create-test-log.ps1

REM Start Filebeat
filebeat.exe -c filebeat-test-simple.yml -e
```

#### Bước 3: Extract Logs từ Elasticsearch
```cmd
python scripts/data_extraction.py --index test-* --output data/raw/logs.csv --hours 24 --host 127.0.0.1 --port 9200
```

#### Bước 4: Preprocess Data
```cmd
python scripts/data_preprocessing.py --input data/raw/logs.csv --output data/processed/logs.csv --clean --extract-time --extract-ip --extract-attack
```

#### Bước 5: Train ML Model
```cmd
python scripts/ml_detector.py --input data/processed/logs.csv --train --model-type isolation_forest --model-file ml_models/model.pkl --output data/predictions.csv
```

#### Bước 6: Write ML Results về Elasticsearch
```cmd
python scripts/elasticsearch_writer.py --input data/predictions.csv --index ml-alerts --host 127.0.0.1 --port 9200
```

#### Bước 7: Xem trong Kibana
1. Mở Kibana: http://localhost:5601
2. Tạo index pattern: `ml-alerts-*`
3. Vào Discover để xem ML predictions

### 4.2 Tạo Test Logs

**SSH Logs:**
```cmd
echo Feb 19 22:35:01 Thien sshd[4000]: Failed password for invalid user admin from 192.168.1.201 port 54328 ssh2 >> C:\Users\thuan\Desktop\test.log
echo Feb 19 22:35:02 Thien sshd[4001]: Failed password for invalid user root from 192.168.1.201 port 54329 ssh2 >> C:\Users\thuan\Desktop\test.log
```

**Web Attack Logs:**
```cmd
echo 192.168.1.201 - - [19/Feb/2026:22:35:04 +0700] "GET /?id=1' OR '1'='1 HTTP/1.1" 200 890 "-" "Mozilla/5.0" >> C:\Users\thuan\Desktop\test.log
```

---

## 5. TỔNG HỢP CODE

### 5.1 Scripts Python Chính

#### data_extraction.py (447 dòng)
- Kết nối Elasticsearch
- Extract logs với Scroll API
- Parse SSH và Web logs từ message
- Detect attacks (brute force)

**Điểm nổi bật:**
- Batch processing để tránh memory overflow
- Fallback parsing khi Logstash chưa parse đầy đủ
- SSH message parsing với regex

#### data_preprocessing.py (234 dòng)
- Clean data (remove duplicates, fill missing values)
- Extract time features (hour, day_of_week, is_weekend)
- Extract IP features (requests_per_ip, ip_hash với MD5)
- Extract attack features (failed_login_count, failed_login_count_window)
- Handle class imbalance (SMOTE, undersampling, oversampling)

**Điểm nổi bật:**
- Window-based failed login count (behavior-based detection)
- IP hashing thay vì encoding (tránh false ordinal relationships)

#### ml_detector.py (341 dòng)
- Isolation Forest (unsupervised)
- One-Class SVM (unsupervised)
- Random Forest (supervised với cross-validation)
- Feature engineering tự động
- Model persistence với joblib

**Điểm nổi bật:**
- Cross-validation với StratifiedKFold
- Class imbalance handling với SMOTE
- ROC AUC score calculation
- Boolean output (True/False) cho Elasticsearch

#### elasticsearch_writer.py (240 dòng)
- Ghi ML predictions vào Elasticsearch
- Boolean field conversion
- Timestamp format conversion (ISO 8601)
- Duplicate detection
- Bulk indexing với error handling

### 5.2 Scripts Bổ Sung

- `ml_evaluator.py`: Comprehensive evaluation với ROC, PR curves
- `compare_methods.py`: So sánh Rule-based vs ML-based
- `false_positive_analyzer.py`: Phân tích False Positives
- `performance_benchmark.py`: Benchmark performance

### 5.3 Dependencies

File: `requirements.txt`

```
elasticsearch>=8.0.0,<9.0.0
pandas>=1.5.0
numpy>=1.23.0
scikit-learn>=1.2.0
joblib>=1.2.0
matplotlib>=3.6.0
seaborn>=0.12.0
pillow>=9.0.0
python-dateutil>=2.8.0
imbalanced-learn>=0.11.0
```

---

## 6. ĐÁNH GIÁ DỰ ÁN

### Điểm Số: 8.9/10 (88-91/100) - XUẤT SẮC 🏆

### Điểm Mạnh

1. **Feature Engineering xuất sắc (9.5/10)**
   - Window-based failed login count
   - Behavior-based detection
   - IP hashing thay vì encoding

2. **Evaluation Layer đầy đủ (9.5/10)**
   - So sánh Rule-based vs ML-based
   - Phân tích False Positives
   - Benchmark performance
   - Visualization ROC, PR curves

3. **Code Quality cao**
   - Error handling tốt
   - Batch processing
   - Modular design
   - Comprehensive comments

4. **Tư duy hệ thống**
   - Không chỉ demo, mà là mini-SIEM thực sự
   - Phân tách rõ ingestion layer và ML layer

### Điểm Cần Cải Thiện

1. **Security (7/10)**
   - Chưa bật xpack.security
   - Chưa có TLS
   - Chưa có authentication

2. **Temporal Validation**
   - Chưa có train/test split theo thời gian
   - Có thể data leakage

3. **Hyperparameter Tuning**
   - Chưa có GridSearchCV
   - Chưa có threshold tuning

4. **Real-time Capability**
   - Pipeline hiện tại là batch processing
   - Chưa có streaming detection

### Kết Luận Từ Giảng Viên

> "Đây là một đồ án có chiều sâu, có tư duy hệ thống, có tư duy ML, có tư duy đánh giá. Không phải đồ án làm cho có điểm. Nó chưa đạt mức research-grade hoàn chỉnh, nhưng vượt mức đồ án môn học thông thường."

---

## 7. ĐẨY LÊN GITHUB

### Repository
https://github.com/thuanthien-tran/elk-based-network-anomaly-detection

### Cách Push

**Script đơn giản:**
```cmd
PUSH_GITHUB_SIMPLE.bat
```

**Hoặc manual:**
```cmd
git add .
git commit -m "Update ELKShield project"
git push origin main
```

### Xác Thực GitHub

Khi push, bạn sẽ cần Personal Access Token:
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Chọn scope: `repo`
4. Copy token và dùng làm password khi push

---

## TROUBLESHOOTING

### Elasticsearch Connection Failed
- Kiểm tra Docker: `docker ps`
- Test: `curl http://127.0.0.1:9200`
- Luôn dùng `--host 127.0.0.1` thay vì `localhost` trên Windows

### Filebeat Không Thu Thập Logs
- Kiểm tra Filebeat đang chạy
- Kiểm tra file log có tồn tại không
- Thêm logs mới vào file để trigger Filebeat

### Python Module Not Found
```cmd
python -m pip install -r requirements.txt
```

### Large File Error khi Push GitHub
- File `filebeat.exe` đã được ignore trong .gitignore
- Nếu vẫn lỗi, xóa khỏi git: `git rm --cached config/filebeat/filebeat.exe`

---

## TỔNG KẾT

Dự án ELKShield đã xây dựng thành công một hệ thống giám sát an ninh mạng tích hợp ELK Stack với Machine Learning. Code được tổ chức rõ ràng, có error handling tốt, và có các tính năng nâng cao như:

- Feature engineering với behavior-based detection
- Comprehensive evaluation và comparison
- Performance benchmarking
- False positive analysis

**Tổng số dòng code:** ~3000+ dòng Python + Config files

**Điểm số:** 8.9/10 (88-91/100) - XUẤT SẮC 🏆

---

**Người tạo:** [Tên sinh viên]  
**Ngày:** 19/02/2026  
**GitHub:** https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
