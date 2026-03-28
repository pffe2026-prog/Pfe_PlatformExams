$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not $env:PLAYWRIGHT_SLOW_MO) {
  $env:PLAYWRIGHT_SLOW_MO = "900"
}

& .\node_modules\.bin\playwright.cmd test playwright\tests\full-demo-flow.spec.js --headed
exit $LASTEXITCODE
