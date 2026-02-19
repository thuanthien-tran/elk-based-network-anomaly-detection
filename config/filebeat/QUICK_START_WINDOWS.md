# 🚀 Quick Start Filebeat trên Windows

## ✅ Trạng Thái Hiện Tại

Filebeat đã khởi động thành công! Tuy nhiên, không có logs nào được thu thập vì các paths Linux (`/var/log/...`) không tồn tại trên Windows.

## 🔧 Giải Pháp Nhanh

### Option 1: Tạo Test Logs (Khuyến nghị cho testing)

1. **Tạo test logs**:
   ```powershell
   # Chạy script PowerShell
   .\create-test-logs.ps1
   ```

2. **Chạy Filebeat với test config**:
   ```cmd
   filebeat.exe -c filebeat-test.yml -e
   ```

3. **Thêm logs mới để test**:
   ```powershell
   # Thêm dòng mới vào test log
   Add-Content -Path "test-logs\ssh-test.log" -Value "Feb 19 22:25:01 Thien sshd[2000]: Failed password for user test from 192.168.1.200 port 54327 ssh2"
   ```

### Option 2: Config cho Windows Paths Thực Tế

1. **Sửa filebeat.yml** để sử dụng Windows paths:

   ```yaml
   filebeat.inputs:
     - type: filestream
       id: ssh-logs-windows
       paths:
         # Uncomment và sửa paths phù hợp với máy bạn
         - C:\ProgramData\ssh\logs\*.log
         # Hoặc tạo log file ở đâu đó
         - D:\logs\ssh\*.log
   ```

2. **Tạo thư mục logs** (nếu chưa có):
   ```cmd
   mkdir D:\logs\ssh
   ```

3. **Copy logs vào đó** hoặc redirect output của ứng dụng vào đó

### Option 3: Dùng Winlogbeat cho Windows Events

Nếu bạn muốn thu thập Windows Event Logs, nên dùng **Winlogbeat** thay vì Filebeat:

```yaml
# winlogbeat.yml
winlogbeat.event_logs:
  - name: System
  - name: Application
  - name: Security
```

## 📊 Kiểm Tra Filebeat Đang Hoạt Động

### 1. Xem Logs của Filebeat

```cmd
type logs\filebeat
```

### 2. Kiểm Tra Metrics

Filebeat sẽ log metrics mỗi 30 giây. Tìm dòng:
```
"message":"Total metrics"
```

Bạn sẽ thấy:
- `harvester.open_files`: Số file đang được monitor
- `harvester.started`: Số harvester đã start
- `events.added`: Số events đã thu thập

### 3. Kiểm Tra trong Kibana

1. Vào Kibana → Discover
2. Chọn index pattern: `ssh-logs-*`, `web-logs-*`, hoặc `test-*`
3. Xem logs real-time

## 🐛 Troubleshooting

### Không có logs được thu thập

**Nguyên nhân**: Paths không tồn tại hoặc không có quyền đọc

**Giải pháp**:
1. Kiểm tra paths có tồn tại:
   ```cmd
   dir C:\ProgramData\ssh\logs
   ```

2. Tạo test logs:
   ```powershell
   .\create-test-logs.ps1
   ```

3. Dùng filebeat-test.yml để test

### Connection refused to Logstash

**Nguyên nhân**: Logstash không chạy hoặc IP sai

**Giải pháp**:
1. Kiểm tra Logstash đang chạy:
   ```bash
   # Trên ELK server
   sudo systemctl status logstash
   ```

2. Test kết nối:
   ```cmd
   telnet your-elk-server-ip 5044
   ```

3. Update IP trong config:
   ```yaml
   output.logstash:
     hosts: ["192.168.1.100:5044"]  # IP thực tế
   ```

### Filebeat không đọc file mới

**Nguyên nhân**: Filebeat đã đọc file và đang chờ thay đổi

**Giải pháp**:
- Thêm dòng mới vào file (append)
- Filebeat sẽ tự động detect và đọc

## 📝 Test Workflow Hoàn Chỉnh

```cmd
# 1. Tạo test logs
powershell -ExecutionPolicy Bypass -File create-test-logs.ps1

# 2. Test config
filebeat.exe test config -c filebeat-test.yml

# 3. Chạy Filebeat
filebeat.exe -c filebeat-test.yml -e

# 4. Trong terminal khác, thêm logs mới
echo Feb 19 22:30:01 Thien sshd[3000]: Test log entry >> test-logs\ssh-test.log

# 5. Kiểm tra trong Kibana
# Vào Kibana → Discover → Chọn index pattern test-*
```

## ✅ Kết Quả Mong Đợi

Sau khi chạy thành công, bạn sẽ thấy trong Kibana:

1. **Logs hiển thị** trong Discover
2. **Fields được parse đúng** (source_ip, user, status, etc.)
3. **Logs real-time** khi thêm dòng mới vào file

## 🎯 Next Steps

1. ✅ Filebeat đã chạy thành công
2. ⏭️ Tạo test logs để verify
3. ⏭️ Config paths thực tế cho Windows
4. ⏭️ Verify logs trong Kibana
5. ⏭️ Setup production paths

---

**Lưu ý**: Filebeat đang chạy nhưng chưa thu thập logs vì paths Linux không tồn tại trên Windows. Hãy tạo test logs hoặc config Windows paths để bắt đầu thu thập!
