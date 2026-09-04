# Stop existing processes on ports 8000 and 5050
$p8000 = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
$p5050 = (Get-NetTCPConnection -LocalPort 5050 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique

if ($p8000) { Stop-Process -Id $p8000 -Force -ErrorAction SilentlyContinue }
if ($p5050) { Stop-Process -Id $p5050 -Force -ErrorAction SilentlyContinue }

Write-Host "Starting Platform Backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000" -NoNewWindow

Start-Sleep -Seconds 2

Write-Host "Starting College ERP Portal on http://127.0.0.1:5050 ..." -ForegroundColor Cyan
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "examples\college-erp\app.py" -NoNewWindow

Write-Host "`nAll services restarted successfully!" -ForegroundColor Green
Write-Host "Open: http://127.0.0.1:5050" -ForegroundColor Yellow
