# ARIA — Install Python locally (no admin, no system Python needed)
# Run from project folder: .\scripts\setup_local_python.ps1
# If pip failed before: delete the .python folder and run this again.

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonDir = Join-Path $ProjectRoot ".python"
$ZipPath = Join-Path $ProjectRoot "python-embed.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$PythonEmbedUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"

# If .python exists but pip is broken, allow re-running by removing .python first
if (Test-Path $PythonDir) {
    $pythonExe = Join-Path $PythonDir "python.exe"
    $hasPip = $false
    if (Test-Path $pythonExe) {
        $pipCheck = & $pythonExe -m pip --version 2>&1
        if ($LASTEXITCODE -eq 0) { $hasPip = $true }
    }
    if ($hasPip) {
        Write-Host "Local Python already exists at .python\" -ForegroundColor Green
        & $pythonExe --version
        exit 0
    }
    Write-Host "Removing existing .python\ (pip was not installed correctly)..." -ForegroundColor Yellow
    Remove-Item -Path $PythonDir -Recurse -Force
}

Write-Host "Downloading Python 3.12 (embeddable, ~25 MB)..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $PythonEmbedUrl -OutFile $ZipPath -UseBasicParsing

Write-Host "Extracting to .python\..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $PythonDir -Force | Out-Null
Expand-Archive -Path $ZipPath -DestinationPath $PythonDir -Force
Remove-Item $ZipPath -Force

# Create Lib\site-packages (required: _pth does not add non-existent paths to sys.path)
$sitePackages = Join-Path $PythonDir "Lib\site-packages"
New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
Write-Host "Created Lib\site-packages" -ForegroundColor Green

# Enable pip: edit the ._pth file
$pthFiles = Get-ChildItem -Path $PythonDir -Filter "python*._pth"
if ($pthFiles.Count -eq 0) { throw "No ._pth file found in embeddable package" }
$pthPath = $pthFiles[0].FullName
$pthContent = Get-Content $pthPath -Raw

# Add Lib\site-packages and uncomment import site (so pip and packages work)
if ($pthContent -notmatch "Lib\\site-packages") {
    $pthContent = $pthContent.TrimEnd() + "`r`nLib\site-packages`r`n"
}
$pthContent = $pthContent -replace "#\s*import site", "import site"
Set-Content -Path $pthPath -Value $pthContent -NoNewline
Write-Host "Configured ._pth for pip" -ForegroundColor Green

# Install pip
$getPipPath = Join-Path $ProjectRoot "get-pip.py"
Write-Host "Downloading get-pip.py..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $GetPipUrl -OutFile $getPipPath -UseBasicParsing

$pythonExe = Join-Path $PythonDir "python.exe"
Write-Host "Installing pip..." -ForegroundColor Cyan
& $pythonExe $getPipPath --no-warn-script-location 2>&1
if ($LASTEXITCODE -ne 0) {
    Remove-Item $getPipPath -Force -ErrorAction SilentlyContinue
    throw "get-pip.py failed. Try deleting .python and running this script again."
}
Remove-Item $getPipPath -Force -ErrorAction SilentlyContinue

# Install dashboard deps
Write-Host "Installing streamlit, pandas, numpy..." -ForegroundColor Cyan
& $pythonExe -m pip install streamlit pandas numpy --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw "pip install failed." }

Write-Host ""
Write-Host "Done. Local Python is at: $PythonDir" -ForegroundColor Green
& $pythonExe --version
Write-Host ""
Write-Host "Run the dashboard with:" -ForegroundColor Yellow
Write-Host "  .\.python\python.exe -m streamlit run aria_dashboard.py" -ForegroundColor White
Write-Host "Or double-click START_DASHBOARD.bat" -ForegroundColor White
