$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$launcher = Join-Path $PSScriptRoot "start_local_demo_fast.ps1"
$urlFile = Join-Path $projectRoot "learn2earn_local_server.url"

& $launcher -NoBrowser

if (-not (Test-Path -LiteralPath $urlFile)) {
  throw "Launcher did not write learn2earn_local_server.url."
}

$url = (Get-Content -Raw -LiteralPath $urlFile).Trim()
if (-not $url.StartsWith("http://127.0.0.1:")) {
  throw "Launcher wrote an unexpected URL: $url"
}

$response = Invoke-WebRequest -Uri ($url + "api/health") -UseBasicParsing -TimeoutSec 5
if ($response.StatusCode -ne 200) {
  throw "Health endpoint returned HTTP $($response.StatusCode)."
}

Write-Host "[PASS] Local launcher is healthy: $url"
