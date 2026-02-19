# PowerShell script to create test logs for Filebeat
# Run this script to generate test log files

$testLogDir = "test-logs"
if (-not (Test-Path $testLogDir)) {
    New-Item -ItemType Directory -Path $testLogDir
    Write-Host "Created directory: $testLogDir" -ForegroundColor Green
}

# Create SSH-like test log
$sshLog = Join-Path $testLogDir "ssh-test.log"
@"
Feb 19 22:20:01 Thien sshd[1234]: Accepted password for user1 from 192.168.1.100 port 54321 ssh2
Feb 19 22:20:05 Thien sshd[1235]: Failed password for invalid user admin from 192.168.1.101 port 54322 ssh2
Feb 19 22:20:10 Thien sshd[1236]: Failed password for invalid user root from 192.168.1.101 port 54323 ssh2
Feb 19 22:20:15 Thien sshd[1237]: Failed password for invalid user admin from 192.168.1.101 port 54324 ssh2
Feb 19 22:20:20 Thien sshd[1238]: Accepted password for user2 from 192.168.1.102 port 54325 ssh2
Feb 19 22:20:25 Thien sshd[1239]: Failed password for invalid user test from 192.168.1.103 port 54326 ssh2
"@ | Out-File -FilePath $sshLog -Encoding UTF8
Write-Host "Created SSH test log: $sshLog" -ForegroundColor Green

# Create web access log (Apache/Common Log Format)
$webLog = Join-Path $testLogDir "web-access.log"
@"
192.168.1.100 - - [19/Feb/2026:22:20:01 +0700] "GET /index.html HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
192.168.1.101 - - [19/Feb/2026:22:20:02 +0700] "GET /admin HTTP/1.1" 401 567 "-" "Mozilla/5.0"
192.168.1.102 - - [19/Feb/2026:22:20:03 +0700] "GET /?id=1' OR '1'='1 HTTP/1.1" 200 890 "-" "Mozilla/5.0"
192.168.1.103 - - [19/Feb/2026:22:20:04 +0700] "GET /script.php?cmd=<script>alert('xss')</script> HTTP/1.1" 200 456 "-" "Mozilla/5.0"
192.168.1.100 - - [19/Feb/2026:22:20:05 +0700] "GET /etc/passwd HTTP/1.1" 403 234 "-" "Mozilla/5.0"
"@ | Out-File -FilePath $webLog -Encoding UTF8
Write-Host "Created web access log: $webLog" -ForegroundColor Green

# Create system log
$systemLog = Join-Path $testLogDir "system-test.log"
@"
Feb 19 22:20:01 Thien kernel: [12345.678] CPU: Temperature above threshold
Feb 19 22:20:02 Thien systemd: Started Network Manager
Feb 19 22:20:03 Thien cron: CRON job executed successfully
Feb 19 22:20:04 Thien kernel: [12346.789] Memory usage: 45%
"@ | Out-File -FilePath $systemLog -Encoding UTF8
Write-Host "Created system test log: $systemLog" -ForegroundColor Green

Write-Host "`nTest logs created successfully!" -ForegroundColor Green
Write-Host "You can now run Filebeat with: filebeat.exe -c filebeat-test.yml -e" -ForegroundColor Yellow
