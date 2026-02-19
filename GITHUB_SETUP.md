# HƯỚNG DẪN SETUP GITHUB REPOSITORY

## BƯỚC 1: Tạo Repository trên GitHub

1. Đăng nhập GitHub: https://github.com
2. Vào: https://github.com/new
3. Repository name: `elk-based-network-anomaly-detection`
4. Description: `ELKShield - Network Security Monitoring System using ELK Stack and Machine Learning`
5. Chọn: **Public** (hoặc Private nếu muốn)
6. **KHÔNG** tích "Initialize with README"
7. Click "Create repository"

---

## BƯỚC 2: Chạy Script Push

### Option A: Batch Script (Windows)
```cmd
push_to_github.bat
```

### Option B: PowerShell Script
```powershell
powershell -ExecutionPolicy Bypass -File push_to_github.ps1
```

### Option C: Manual Commands
```cmd
REM 1. Initialize git (nếu chưa có)
git init

REM 2. Add remote
git remote add origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git

REM 3. Add files
git add .

REM 4. Commit
git commit -m "Initial commit: ELKShield Network Security Monitoring System"

REM 5. Push
git branch -M main
git push -u origin main
```

---

## BƯỚC 3: Xác Thực GitHub

Khi push, bạn sẽ được yêu cầu xác thực. Có 3 cách:

### Cách 1: Personal Access Token (Khuyến nghị)

1. Tạo token:
   - GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token (classic)
   - Chọn scopes: `repo` (full control)
   - Copy token

2. Khi push:
   - Username: `thuanthien-tran`
   - Password: `[paste token here]`

### Cách 2: GitHub CLI

```cmd
REM Cài GitHub CLI
winget install GitHub.cli

REM Login
gh auth login

REM Push
git push -u origin main
```

### Cách 3: SSH Key

```cmd
REM Tạo SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

REM Copy public key
type %USERPROFILE%\.ssh\id_ed25519.pub

REM Add vào GitHub: Settings → SSH and GPG keys → New SSH key

REM Đổi remote URL
git remote set-url origin git@github.com:thuanthien-tran/elk-based-network-anomaly-detection.git
```

---

## KIỂM TRA TRƯỚC KHI PUSH

### 1. Kiểm tra .gitignore
Các file sau sẽ KHÔNG được commit (đã có trong .gitignore):
- ✅ `data/` (CSV files, logs)
- ✅ `ml_models/*.pkl` (model files)
- ✅ `*.log` (log files)
- ✅ `__pycache__/` (Python cache)
- ✅ `.vscode/`, `.idea/` (IDE settings)

### 2. Files sẽ được commit:
- ✅ Tất cả Python scripts (`scripts/*.py`)
- ✅ Config files (`config/`, `docker/`)
- ✅ Documentation (`*.md`, `TONG_HOP_CODE_FINAL.docx`)
- ✅ `requirements.txt`
- ✅ `setup.bat`
- ✅ `.gitignore`

---

## SAU KHI PUSH THÀNH CÔNG

1. Kiểm tra repository: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection
2. Thêm README.md mô tả project (nếu chưa có)
3. Thêm LICENSE (nếu cần)
4. Tạo releases/tags cho các phiên bản

---

## TROUBLESHOOTING

### Lỗi: "Repository not found"
- Kiểm tra repository đã được tạo trên GitHub chưa
- Kiểm tra URL: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection

### Lỗi: "Authentication failed"
- Setup Personal Access Token
- Hoặc dùng GitHub CLI: `gh auth login`

### Lỗi: "Large files"
- File lớn đã được ignore trong .gitignore
- Nếu vẫn lỗi, kiểm tra file nào lớn:
```cmd
git ls-files | xargs ls -lh | sort -k5 -hr | head -10
```

---

**Chúc bạn thành công!** 🚀
