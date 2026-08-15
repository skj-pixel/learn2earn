param(
  [Parameter(Mandatory = $true)][string]$Version,
  [Parameter(Mandatory = $true)][string]$Tag,
  [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$mainRepo = Resolve-Path (Join-Path $PSScriptRoot '..')
$releaseRoot = Join-Path $env:LOCALAPPDATA "Learn2Earn\release-worktrees\$Version"
$tagCommit = (& git -C $mainRepo rev-parse "$Tag^{commit}" 2>$null).Trim()
if (-not $tagCommit) { throw "Release tag not found: $Tag" }

function Test-Ready([string]$Url) {
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
    return $response.StatusCode -eq 200
  } catch { return $false }
}

function Test-PortFree([int]$Port) {
  $listener = $null
  try {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    $listener.Start()
    return $true
  } catch { return $false } finally { if ($listener) { $listener.Stop() } }
}

try {
  Write-Host "[Learn2Earn $Version] Preparing fixed release $Tag..." -ForegroundColor Cyan

  if (-not (Test-Path -LiteralPath (Join-Path $releaseRoot '.git'))) {
    New-Item -ItemType Directory -Path (Split-Path $releaseRoot) -Force | Out-Null
    & git -C $mainRepo worktree add --detach $releaseRoot $tagCommit
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the fixed release worktree.' }
  }

  $actualCommit = (& git -C $releaseRoot rev-parse HEAD 2>$null).Trim()
  if ($actualCommit -ne $tagCommit) {
    throw "The release cache contains a different version. Remove '$releaseRoot' and start again."
  }

  $sitePackages = Join-Path $mainRepo '.venv\Lib\site-packages'
  $basePython = 'D:\anaconda3\python.exe'
  if (-not (Test-Path -LiteralPath $basePython)) { throw "Python not found: $basePython" }
  if (-not (Test-Path -LiteralPath $sitePackages)) { throw 'Prepared Python dependencies are missing in the main repository.' }

  $releaseModules = Join-Path $releaseRoot 'frontend\node_modules'
  if (-not (Test-Path -LiteralPath $releaseModules)) {
    $mainModules = Join-Path $mainRepo 'frontend\node_modules'
    if (-not (Test-Path -LiteralPath $mainModules)) { throw 'Frontend dependencies are missing in the main repository.' }
    New-Item -ItemType Junction -Path $releaseModules -Target $mainModules | Out-Null
  }

  $frontendIndex = Join-Path $releaseRoot 'frontend\dist\index.html'
  if (-not (Test-Path -LiteralPath $frontendIndex)) {
    Write-Host "[Learn2Earn $Version] Building this release's frontend (first launch only)..."
    & npm.cmd --prefix (Join-Path $releaseRoot 'frontend') run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
  }

  $port = 9000..9010 | Where-Object { Test-PortFree $_ } | Select-Object -First 1
  if ($null -eq $port) { throw 'Ports 9000-9010 are occupied.' }
  $url = "http://127.0.0.1:$port/"
  $database = Join-Path $mainRepo 'backend\app\learn2earn.db'
  if (-not (Test-Path -LiteralPath $database)) { throw "Database not found: $database" }

  $arch = $env:PROCESSOR_ARCHITECTURE
  $pythonCode = "import os,platform; platform.machine=lambda:os.environ.get('PROCESSOR_ARCHITECTURE','AMD64'); import uvicorn; uvicorn.run('backend.app.main:app',host='127.0.0.1',port=$port,log_level='warning',lifespan='off')"
  $startInfo = [Diagnostics.ProcessStartInfo]::new()
  $startInfo.FileName = $basePython
  $startInfo.Arguments = "-c `"$pythonCode`""
  $startInfo.WorkingDirectory = $releaseRoot
  $startInfo.UseShellExecute = $false
  $startInfo.CreateNoWindow = $true
  $startInfo.EnvironmentVariables['PROCESSOR_ARCHITECTURE'] = $arch
  $startInfo.EnvironmentVariables['PYTHONPATH'] = "$sitePackages;$releaseRoot"
  $startInfo.EnvironmentVariables['LEARN2EARN_DATABASE_PATH'] = $database
  $server = [Diagnostics.Process]::Start($startInfo)
  if (-not $server) { throw 'Backend process could not be created.' }

  $deadline = [DateTime]::UtcNow.AddSeconds(120)
  $nextProgress = [DateTime]::UtcNow.AddSeconds(10)
  while ([DateTime]::UtcNow -lt $deadline -and -not $server.HasExited) {
    if (Test-Ready "${url}api/health") { break }
    if ([DateTime]::UtcNow -ge $nextProgress) {
      Write-Host "[Learn2Earn $Version] Backend is loading..."
      $nextProgress = [DateTime]::UtcNow.AddSeconds(10)
    }
    Start-Sleep -Milliseconds 250
  }
  if ($server.HasExited -or -not (Test-Ready "${url}api/health")) {
    if (-not $server.HasExited) { $server.Kill() }
    throw 'Backend did not become ready within 120 seconds.'
  }

  Write-Host "[Learn2Earn $Version] Ready: $url" -ForegroundColor Green
  if (-not $NoBrowser) { Start-Process $url }
  Write-Host 'Keep this window open. Press Ctrl+C to stop.'
  $server.WaitForExit()
} catch {
  Write-Host "[Learn2Earn $Version] Startup failed: $($_.Exception.Message)" -ForegroundColor Red
  Read-Host 'Press Enter to close'
  exit 1
} finally {
  if ($server -and -not $server.HasExited) { $server.Kill() }
}
