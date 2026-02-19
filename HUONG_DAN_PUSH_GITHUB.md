# HƯỚNG DẪN ĐẨY DỰ ÁN LÊN GITHUB

## CÁCH 1: Sử dụng Script Tự Động (Khuyến nghị)

### Windows Batch Script:
```cmd
push_to_github.bat
```

### PowerShell Script:
```powershell
powershell -ExecutionPolicy Bypass -File push_to_github.ps1
```

Script sẽ tự động:
1. Kiểm tra Git đã cài chưa
2. Khởi tạo git repository (nếu chưa có)
3. Thêm remote repository
4. Add tất cả files
5. Commit với message
6. Push lên GitHub

---

## CÁCH 2: Làm Thủ Công

### Bước 1: Cài đặt Git (nếu chưa có)
Download từ: https://git-scm.com/download/win

### Bước 2: Cấu hình Git (lần đầu)
```cmd
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Bước 3: Khởi tạo Repository
```cmd
cd "D:\Do An\Do An An Toan Mang\ELKShield An Intelligent Network Security Monitoring System using Machine Learning"

REM Nếu chưa có .git
git init

REM Thêm remote
git remote add origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git
```

### Bước 4: Add và Commit
```cmd
REM Add tất cả files (trừ những file trong .gitignore)
git add .

REM Commit
git commit -m "Initial commit: ELKShield Network Security Monitoring System"
```

### Bước 5: Push lên GitHub
```cmd
REM Push lên branch main
git branch -M main
git push -u origin main
```

---

## XÁC THỰC VỚI GITHUB

### Option 1: Personal Access Token (Khuyến nghị)

1. Tạo Personal Access Token:
   - Vào GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token (classic)
   - Chọn scopes: `repo` (full control)
   - Copy token

2. Khi push, nhập:
   - Username: `thuanthien-tran`
   - Password: `[paste token here]`

### Option 2: GitHub CLI

```cmd
REM Cài GitHub CLI
winget install GitHub.cli

REM Login
gh auth login

REM Push
git push -u origin main
```

### Option 3: SSH Key

1. Tạo SSH key:
```cmd
ssh-keygen -t ed25519 -C "your.email@example.com"
```

2. Copy public key và add vào GitHub:
   - Settings → SSH and GPG keys → New SSH key
   - Paste nội dung file `~/.ssh/id_ed25519.pub`

3. Đổi remote URL:
```cmd
git remote set-url origin git@github.com:thuanthien-tran/elk-based-network-anomaly-detection.git
```

---

## KIỂM TRA TRƯỚC KHI PUSH

### 1. Kiểm tra .gitignore
Đảm bảo các file sau KHÔNG được commit:
- `data/` (logs, CSV files)
- `ml_models/*.pkl` (model files lớn)
- `reports/` (có thể commit nếu nhỏ)
- `.env`, `*.key`, `*.pem` (credentials)
- `__pycache__/`, `*.pyc`
- `.idea/`, `.vscode/` (IDE settings)

### 2. Kiểm tra file size
GitHub có giới hạn:
- File đơn lẻ: 100MB
- Repository: 1GB (free)

Nếu có file lớn, dùng Git LFS:
```cmd
git lfs install
git lfs track "*.pkl"
git lfs track "data/**"
```

### 3. Kiểm tra thông tin nhạy cảm
Đảm bảo KHÔNG commit:
- Passwords
- API keys
- Private keys
- Personal information

---

## CẤU TRÚC REPOSITORY TRÊN GITHUB

Sau khi push, repository sẽ có cấu trúc:

```
elk-based-network-anomaly-detection/
├── README.md
├── requirements.txt
├── setup.bat
├── .gitignore
├── docker/
│   └── docker-compose.yml
├── config/
│   ├── filebeat/
│   │   └── filebeat-test-simple.yml
│   └── logstash/
│       └── pipeline.conf
├── scripts/
│   ├── data_extraction.py
│   ├── data_preprocessing.py
│   ├── ml_detector.py
│   ├── elasticsearch_writer.py
│   ├── ml_evaluator.py
│   ├── compare_methods.py
│   ├── false_positive_analyzer.py
│   ├── performance_benchmark.py
│   └── ...
├── docs/
│   └── ...
└── HUONG_DAN_CHAY_DU_AN.md
```

---

## TROUBLESHOOTING

### Lỗi: "Repository not found"
- Kiểm tra repository đã được tạo trên GitHub chưa
- Kiểm tra bạn có quyền truy cập không
- Kiểm tra URL remote đúng chưa

### Lỗi: "Authentication failed"
- Setup Personal Access Token
- Hoặc dùng GitHub CLI: `gh auth login`
- Hoặc setup SSH key

### Lỗi: "Large files"
- Dùng Git LFS cho file lớn
- Hoặc xóa file khỏi git history:
```cmd
git rm --cached large_file.pkl
git commit -m "Remove large file"
```

### Lỗi: "Branch main does not exist"
```cmd
git branch -M main
git push -u origin main
```

---

## LƯU Ý QUAN TRỌNG

1. **KHÔNG commit file nhạy cảm**: passwords, keys, credentials
2. **KHÔNG commit data files lớn**: dùng Git LFS hoặc để trong .gitignore
3. **KHÔNG commit model files lớn**: chỉ commit code, không commit trained models
4. **Commit message rõ ràng**: mô tả những gì đã thay đổi

---

## SAU KHI PUSH THÀNH CÔNG

1. Kiểm tra trên GitHub: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
2. Thêm README.md mô tả project (nếu chưa có)
3. Thêm LICENSE nếu cần
4. Thêm badges (nếu muốn)
5. Tạo releases/tags cho các phiên bản quan trọng

---

**Chúc bạn thành công!** 🚀
