$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

function Select-Or-Create-Python {
  $candidates = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    (Join-Path $projectRoot "work_verify_venv\Scripts\python.exe"),
    (Join-Path $projectRoot "backend\learn2earn\Scripts\python.exe")
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
      $previousPreference = $ErrorActionPreference
      try {
        $ErrorActionPreference = "Continue"
        & $candidate -m pip install --help 2>&1 | Out-Null
        $pipExitCode = $LASTEXITCODE
      } finally {
        $ErrorActionPreference = $previousPreference
      }
      if ($pipExitCode -eq 0) {
        return $candidate
      }
      Write-Host "[Learn2Earn] Skipping broken virtual environment: $candidate"
    }
  }
  Write-Host "[Learn2Earn] No virtual environment found. Creating .venv ..."
  python -m venv ".venv"
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create .venv. Please install Python 3.10+."
  }
  return (Join-Path $projectRoot ".venv\Scripts\python.exe")
}

$python = Select-Or-Create-Python

Write-Host "[Learn2Earn] Installing/checking backend dependencies..."
& $python -m pip install -r "backend\requirements.txt"
if ($LASTEXITCODE -ne 0) {
  throw "Backend dependency installation failed."
}

Write-Host "[Learn2Earn] Installing/checking frontend dependencies..."
Push-Location "frontend"
try {
  # NOTE: keep this file ASCII-only. It has NO UTF-8 BOM, and Windows PowerShell 5.1
  # on a zh-CN machine would decode non-ASCII bytes as GBK and fail at parse time.
  #
  # 'npm ci' wipes node_modules before reinstalling, which is the correct cure for a
  # partially corrupted tree (cloud-sync tools can silently strip nested packages).
  # But the wipe itself can be refused by antivirus, file locks, or a sync client
  # holding handles. In that case fall back to the non-destructive 'npm install',
  # which repairs missing packages in place instead of giving up entirely.
  $installOk = $false
  if (Test-Path -LiteralPath "package-lock.json") {
    npm ci
    if ($LASTEXITCODE -eq 0) {
      $installOk = $true
    } else {
      Write-Host "[Learn2Earn] 'npm ci' failed (node_modules may be locked by a sync client or antivirus)."
      Write-Host "[Learn2Earn] Falling back to incremental 'npm install' ..."
    }
  }
  if (-not $installOk) {
    npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) {
      throw "Frontend dependency installation failed."
    }
  }

  Write-Host "[Learn2Earn] Building frontend dist..."
  npm run build
  if ($LASTEXITCODE -ne 0) {
    throw "Frontend build failed."
  }
} finally {
  Pop-Location
}

& $python -c "import fastapi, uvicorn, sqlalchemy, pydantic, aiosqlite, httpx; print('backend dependencies ok')"
if ($LASTEXITCODE -ne 0) {
  throw "Backend dependency verification failed."
}

$indexPath = "frontend\dist\index.html"
if (-not (Test-Path -LiteralPath $indexPath)) {
  throw "frontend\dist\index.html is missing after the build."
}

$assetsDir = "frontend\dist\assets"
if (-not (Test-Path -LiteralPath $assetsDir)) {
  throw "frontend\dist\assets is missing after the build."
}

$html = Get-Content -LiteralPath $indexPath -Raw
$refs = [regex]::Matches($html, '/assets/[A-Za-z0-9._-]+')
if ($refs.Count -eq 0) {
  throw "frontend\dist\index.html references no asset files; the build output looks truncated."
}
foreach ($match in $refs) {
  $relative = $match.Value.TrimStart('/') -replace '/', '\'
  $fullPath = Join-Path "frontend\dist" $relative
  if (-not (Test-Path -LiteralPath $fullPath)) {
    throw "Frontend build is incomplete: missing $($match.Value)"
  }
}
Write-Host "[Learn2Earn] Frontend build verified: $($refs.Count) asset references all present."

Write-Host "[Learn2Earn] Preparation complete. Daily startup will not install dependencies."
