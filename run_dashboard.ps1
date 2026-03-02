# Run ARIA Virtual Test Dashboard (PowerShell)
# From project folder: .\run_dashboard.ps1

$packages = @("streamlit", "pandas", "numpy")
foreach ($p in $packages) {
    if (-not (python -m pip show $p 2>$null)) {
        Write-Host "Installing $p..."
        python -m pip install $p --quiet
    }
}
Write-Host "`nStarting ARIA dashboard..."
Write-Host "Open http://localhost:8501 in your browser. Press Ctrl+C to stop.`n"
python -m streamlit run aria_dashboard.py
