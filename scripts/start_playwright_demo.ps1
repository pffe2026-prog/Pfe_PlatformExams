$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$env:PLAYWRIGHT_DEMO_MODE = "1"
$env:API_WEBHOOK_TOKEN = "playwright-demo-token"

& .\.venv\Scripts\python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

& .\.venv\Scripts\python scripts\seed_playwright_demo.py
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

& .\.venv\Scripts\python manage.py runserver 127.0.0.1:8000 --noreload
exit $LASTEXITCODE
