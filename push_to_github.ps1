# PowerShell script to push ELKShield project to GitHub
# Repository: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pushing ELKShield Project to GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "[OK] Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Git is not installed!" -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Check if already a git repository
if (Test-Path ".git") {
    Write-Host "[INFO] Git repository already initialized" -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Initializing git repository..." -ForegroundColor Yellow
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to initialize git repository" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Git repository initialized" -ForegroundColor Green
}

Write-Host ""

# Check remote
Write-Host "Checking remote repository..." -ForegroundColor Yellow
$remotes = git remote -v
if ($remotes -notmatch "elk-based-network-anomaly-detection") {
    Write-Host "[INFO] Adding remote repository..." -ForegroundColor Yellow
    git remote add origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARNING] Remote might already exist, trying to set URL..." -ForegroundColor Yellow
        git remote set-url origin https://github.com/thuanthien-tran/elk-based-network-anomaly-detection.git
    }
    Write-Host "[OK] Remote repository added" -ForegroundColor Green
} else {
    Write-Host "[OK] Remote repository already configured" -ForegroundColor Green
}

Write-Host ""

# Add all files
Write-Host "Adding files to git..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to add files" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if there are changes to commit
$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "[INFO] No changes to commit" -ForegroundColor Yellow
    Write-Host "Checking if we need to push..." -ForegroundColor Yellow
    
    # Check if local is ahead of remote
    $localCommits = git log origin/main..HEAD --oneline 2>$null
    if ([string]::IsNullOrWhiteSpace($localCommits)) {
        Write-Host "[INFO] Everything is up to date!" -ForegroundColor Green
        Read-Host "Press Enter to exit"
        exit 0
    }
} else {
    Write-Host "[INFO] Files staged for commit" -ForegroundColor Green
}

Write-Host ""

# Commit
Write-Host "Committing changes..." -ForegroundColor Yellow
$commitMsg = Read-Host "Enter commit message (or press Enter for default)"
if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    $commitMsg = "Update ELKShield project code and documentation"
}

git commit -m $commitMsg
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] Commit failed or no changes to commit" -ForegroundColor Yellow
}

Write-Host ""

# Push to GitHub
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "[INFO] This may require GitHub credentials" -ForegroundColor Yellow
Write-Host ""

# Determine branch name
$currentBranch = git branch --show-current
if ($currentBranch -notmatch "main|master") {
    Write-Host "[INFO] Current branch: $currentBranch" -ForegroundColor Yellow
    Write-Host "[INFO] Creating/checking out main branch..." -ForegroundColor Yellow
    git checkout -b main 2>$null
    if ($LASTEXITCODE -ne 0) {
        git checkout main 2>$null
    }
    $currentBranch = "main"
}

# Push
Write-Host "Pushing to origin/$currentBranch..." -ForegroundColor Yellow
git push -u origin $currentBranch

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to push to GitHub" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible reasons:" -ForegroundColor Yellow
    Write-Host "1. Not authenticated with GitHub"
    Write-Host "2. Repository doesn't exist or you don't have access"
    Write-Host "3. Network issues"
    Write-Host ""
    Write-Host "Solutions:" -ForegroundColor Yellow
    Write-Host "1. Setup GitHub authentication:"
    Write-Host "   git config --global user.name `"Your Name`""
    Write-Host "   git config --global user.email `"your.email@example.com`""
    Write-Host ""
    Write-Host "2. Use GitHub Desktop or GitHub CLI for easier authentication"
    Write-Host "   GitHub CLI: gh auth login"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "[SUCCESS] Project pushed to GitHub!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Repository URL: https://github.com/thuanthien-tran/elk-based-network-anomaly-detection" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
