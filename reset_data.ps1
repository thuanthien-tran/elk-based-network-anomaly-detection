# PowerShell script to reset all data for fresh attack simulation
# More reliable than batch file for Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESET DATA - ELKShield Project" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[WARNING] This will delete all test-logs-* and ml-alerts-* indices!" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Are you sure? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "[1/5] Listing current indices..." -ForegroundColor Green
$indices = (Invoke-RestMethod -Uri "http://127.0.0.1:9200/_cat/indices?v" -Method Get) | Out-String
Write-Host $indices

Write-Host "[2/5] Getting list of test-logs-* indices..." -ForegroundColor Green
try {
    $testLogsIndices = (Invoke-RestMethod -Uri "http://127.0.0.1:9200/_cat/indices/test-logs-*?h=index" -Method Get) -split "`n" | Where-Object { $_.Trim() -ne "" }
    foreach ($index in $testLogsIndices) {
        $index = $index.Trim()
        if ($index) {
            Write-Host "  Deleting index: $index" -ForegroundColor Yellow
            try {
                Invoke-RestMethod -Uri "http://127.0.0.1:9200/$index" -Method Delete | Out-Null
                Write-Host "    [OK] Deleted: $index" -ForegroundColor Green
            } catch {
                Write-Host "    [ERROR] Failed to delete: $index" -ForegroundColor Red
            }
        }
    }
    Write-Host "[OK] test-logs-* indices deleted" -ForegroundColor Green
} catch {
    Write-Host "[INFO] No test-logs-* indices found or error: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/5] Getting list of ml-alerts-* indices..." -ForegroundColor Green
try {
    $mlAlertsIndices = (Invoke-RestMethod -Uri "http://127.0.0.1:9200/_cat/indices/ml-alerts-*?h=index" -Method Get) -split "`n" | Where-Object { $_.Trim() -ne "" }
    foreach ($index in $mlAlertsIndices) {
        $index = $index.Trim()
        if ($index) {
            Write-Host "  Deleting index: $index" -ForegroundColor Yellow
            try {
                Invoke-RestMethod -Uri "http://127.0.0.1:9200/$index" -Method Delete | Out-Null
                Write-Host "    [OK] Deleted: $index" -ForegroundColor Green
            } catch {
                Write-Host "    [ERROR] Failed to delete: $index" -ForegroundColor Red
            }
        }
    }
    Write-Host "[OK] ml-alerts-* indices deleted" -ForegroundColor Green
} catch {
    Write-Host "[INFO] No ml-alerts-* indices found or error: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[4/5] Verifying deletion..." -ForegroundColor Green
Start-Sleep -Seconds 2
$remaining = (Invoke-RestMethod -Uri "http://127.0.0.1:9200/_cat/indices?v" -Method Get) | Out-String
$testLogsRemaining = $remaining | Select-String -Pattern "test-logs"
$mlAlertsRemaining = $remaining | Select-String -Pattern "ml-alerts"

if ($testLogsRemaining -or $mlAlertsRemaining) {
    Write-Host "[WARNING] Some indices still exist!" -ForegroundColor Yellow
    Write-Host $remaining
} else {
    Write-Host "[OK] All test-logs-* and ml-alerts-* indices deleted" -ForegroundColor Green
}

Write-Host ""
Write-Host "[5/5] Cleaning old CSV files..." -ForegroundColor Green
$csvFiles = @(
    "data\raw\logs.csv",
    "data\processed\logs.csv",
    "data\predictions.csv",
    "data\processed\logs_with_ml.csv"
)
foreach ($file in $csvFiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        Write-Host "  [OK] Deleted: $file" -ForegroundColor Green
    }
}

$delModel = Read-Host "Delete old ML model? (yes/no)"
if ($delModel -eq "yes") {
    if (Test-Path "ml_models\model.pkl") {
        Remove-Item "ml_models\model.pkl" -Force
        Write-Host "[OK] ML model deleted" -ForegroundColor Green
    }
} else {
    Write-Host "[SKIP] ML model kept" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Reset completed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Final index status:" -ForegroundColor Green
Invoke-RestMethod -Uri "http://127.0.0.1:9200/_cat/indices?v" -Method Get
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Create new test.log file with attack logs"
Write-Host "2. Restart Filebeat: cd config\filebeat; filebeat.exe -c filebeat-test-simple.yml -e"
Write-Host "3. Run ML pipeline again"
Write-Host ""
