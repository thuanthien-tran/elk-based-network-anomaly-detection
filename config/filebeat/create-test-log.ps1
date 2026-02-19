# PowerShell script to create test.log on Desktop
$testLogPath = "C:\Users\thuan\Desktop\test.log"

$content = @"
Feb 19 22:20:01 Thien sshd[1234]: Accepted password for user1 from 192.168.1.100 port 54321 ssh2
Feb 19 22:20:05 Thien sshd[1235]: Failed password for invalid user admin from 192.168.1.101 port 54322 ssh2
Feb 19 22:20:10 Thien sshd[1236]: Failed password for invalid user root from 192.168.1.101 port 54323 ssh2
Feb 19 22:20:15 Thien sshd[1237]: Failed password for invalid user admin from 192.168.1.101 port 54324 ssh2
Feb 19 22:20:20 Thien sshd[1238]: Accepted password for user2 from 192.168.1.102 port 54325 ssh2
192.168.1.100 - - [19/Feb/2026:22:20:01 +0700] "GET /index.html HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
192.168.1.101 - - [19/Feb/2026:22:20:02 +0700] "GET /admin HTTP/1.1" 401 567 "-" "Mozilla/5.0"
192.168.1.102 - - [19/Feb/2026:22:20:03 +0700] "GET /?id=1' OR '1'='1 HTTP/1.1" 200 890 "-" "Mozilla/5.0"
192.168.1.103 - - [19/Feb/2026:22:20:04 +0700] "GET /script.php?cmd=<script>alert('xss')</script> HTTP/1.1" 200 456 "-" "Mozilla/5.0"
Feb 19 22:20:25 Thien sshd[1239]: Failed password for invalid user test from 192.168.1.103 port 54326 ssh2
"@

$content | Out-File -FilePath $testLogPath -Encoding UTF8 -NoNewline

Write-Host "Created test.log at: $testLogPath" -ForegroundColor Green
Write-Host "File contains sample SSH and web logs for testing Filebeat" -ForegroundColor Green
