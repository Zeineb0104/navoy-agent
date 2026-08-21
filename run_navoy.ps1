# run_navoy.ps1 — Navoy setup and launch script

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Navoy Travel Recommendation System" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pyver = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "not found" }
    Write-Host "[OK] $pyver" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python:" -ForegroundColor Yellow
    Write-Host "  1. Open: https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "  2. Download Python 3.12" -ForegroundColor White
    Write-Host "  3. Run installer -> CHECK 'Add Python to PATH'" -ForegroundColor White
    Write-Host "  4. Re-run this script" -ForegroundColor White
    Write-Host ""
    Start-Process "https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2 - Move to script directory
Set-Location $PSScriptRoot
Write-Host "[INFO] Directory: $PSScriptRoot" -ForegroundColor Gray

# Step 3 - Install dependencies if needed
Write-Host ""
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$streamlitCheck = & streamlit --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installing packages from requirements.txt..." -ForegroundColor Yellow
    & pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] pip install failed." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Packages installed!" -ForegroundColor Green
} else {
    Write-Host "[OK] Dependencies already installed: $streamlitCheck" -ForegroundColor Green
}

# Step 4 - Launch
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Launching app at http://localhost:8501" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

& streamlit run app.py --server.headless false --browser.gatherUsageStats false
