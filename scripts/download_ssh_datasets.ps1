# Download SSH datasets (University of Twente) - direct links from simpleweb.org/wiki/SSH_datasets
# Chay trong PowerShell: .\scripts\download_ssh_datasets.ps1

$baseUrl = "http://traces.simpleweb.org/ssh_datasets"
$outDir  = "data\datasets\ssh_twente"
$null    = New-Item -ItemType Directory -Force -Path $outDir

# Dataset 1 - Log files (12 MB)
$url1 = "$baseUrl/dataset1_log_files.tgz"
$out1 = Join-Path $outDir "dataset1_log_files.tgz"
Write-Host "Downloading dataset1_log_files.tgz (12 MB)..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $url1 -OutFile $out1 -UseBasicParsing
Write-Host "Saved: $out1" -ForegroundColor Green

# Dataset 2 - Log files (101 MB)
$url2 = "$baseUrl/dataset2_log_files.tgz"
$out2 = Join-Path $outDir "dataset2_log_files.tgz"
Write-Host "Downloading dataset2_log_files.tgz (101 MB)..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $url2 -OutFile $out2 -UseBasicParsing
Write-Host "Saved: $out2" -ForegroundColor Green

Write-Host "`nDone. Extract with: tar -xzf dataset1_log_files.tgz (or use 7-Zip)" -ForegroundColor Yellow
