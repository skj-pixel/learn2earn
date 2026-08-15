param(
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

# ---- Refresh current session env block from registry (User + Machine) ----
# 🔍 [作用] Windows 设置环境变量后只更新注册表，不更新当前 PowerShell 会话的环境块；
#          这里把 HKCU\Environment + HKLM\System\CurrentControlSet\Control\Session Manager\Environment
#          合并到当前会话，让新设的 doubao_cloud_api 等变量能被子进程继承。
# 🔍 [语法] [Microsoft.Win32.Registry] 类 + RegistryKey.OpenBaseKey + GetValue
# 🔍 [陷阱] Process scope 优先保留（避免覆盖本会话已 set 的）；使用 -ErrorAction SilentlyContinue 跳过不可访问的项。
try {
  $protectedProcessVars = @('PATH', 'TEMP', 'TMP')
  $hkcu = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment')
  if ($hkcu) {
    foreach ($name in $hkcu.GetValueNames()) {
      if (-not $name) { continue }
      try {
        $val = $hkcu.GetValue($name)
        if ($null -ne $val -and $name -notin $protectedProcessVars) {
          Set-Item -Path "Env:\$name" -Value ([string]$val) -ErrorAction SilentlyContinue
        }
      } catch {}
    }
    $hkcu.Close()
  }
  $hklm = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SYSTEM\CurrentControlSet\Control\Session Manager\Environment')
  if ($hklm) {
    foreach ($name in $hklm.GetValueNames()) {
      if (-not $name) { continue }
      try {
        $val = $hklm.GetValue($name)
        if ($null -ne $val -and $name -notin $protectedProcessVars) {
          Set-Item -Path "Env:\$name" -Value ([string]$val) -ErrorAction SilentlyContinue
        }
      } catch {}
    }
    $hklm.Close()
  }
  Write-Host "[Learn2Earn] Refreshed env block from HKCU\Environment + HKLM\System\CurrentControlSet\Control\Session Manager\Environment."
} catch {
  Write-Host "[Learn2Earn] WARNING: Could not refresh env from registry ($($_.Exception.Message)). New env vars may not be picked up."
}

# ---- Read LLM API Key from user-level env var (avoid hardcoding in repo/code) ----
$envLlmKey = $env:LEARN2EARN_LLM_API_KEY
if ($envLlmKey -and $envLlmKey.Trim()) {
    $masked = if ($envLlmKey.Length -gt 8) { $envLlmKey.Substring(0,4) + "****" + $envLlmKey.Substring($envLlmKey.Length - 4) } else { "****" }
    Write-Host "[Learn2Earn] LLM API Key injected via env var LEARN2EARN_LLM_API_KEY (masked: $masked). Not written to code or config."
} else {
    Write-Host "[Learn2Earn] WARNING: env var LEARN2EARN_LLM_API_KEY not set; LLM calls will fail. Set it in System Environment Variables, then re-run this script."
}

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$logFile = Join-Path $projectRoot "learn2earn_local_server.log"
$errLogFile = Join-Path $projectRoot "learn2earn_local_server.err.log"
$pidFile = Join-Path $projectRoot "learn2earn_local_server.pid"
$urlFile = Join-Path $projectRoot "learn2earn_local_server.url"
$env:LEARN2EARN_DATABASE_PATH = Join-Path $projectRoot "backend\app\learn2earn.db"
Write-Host "[Learn2Earn] Database: $env:LEARN2EARN_DATABASE_PATH"

# ---- Auto-load demo seed when the local data files are missing or empty ----
# 🔍 [作用] 让任何克隆仓库的人双击启动 .bat 后，第一次启动自动从 seed/ 加载演示数据
#          （33 科目 / 30 笔记 / 103 产品 / 40 任务 / 904 技能），避免看到空白 WebUI。
#          已运行过的用户（db 大于 1MB）不会被覆盖，保留他们自己的数据。
# 🔍 [陷阱] 必须用 -LiteralPath，路径含中文与空格时 -Path 会被当通配符解析
function Initialize-SeedData {
  $dbPath = $env:LEARN2EARN_DATABASE_PATH
  $seedDb = Join-Path $projectRoot "seed\learn2earn.db"
  $seedLlm = Join-Path $projectRoot "seed\llm_config.json"
  $seedStorageTar = Join-Path $projectRoot "seed\storage.tar.gz"
  $storagePath = Join-Path $projectRoot "storage"

  $dbEmpty = $true
  if (Test-Path -LiteralPath $dbPath) {
    $dbSize = (Get-Item -LiteralPath $dbPath).Length
    if ($dbSize -gt 1000000) {
      $dbEmpty = $false
    }
  }
  if ($dbEmpty) {
    if (Test-Path -LiteralPath $seedDb) {
      Write-Host "[Learn2Earn] Empty database detected. Loading demo seed database..."
      Copy-Item -LiteralPath $seedDb -Destination $dbPath -Force
      Write-Host "[Learn2Earn] Demo database loaded: 33 subjects / 30 notes / 103 products / 40 generation tasks / 904 installed skills."
    } else {
      Write-Host "[Learn2Earn] WARNING: No demo seed found at $seedDb. Database will start empty."
    }
  }

  $llmConfigPath = Join-Path $projectRoot "backend\llm_config.json"
  if (-not (Test-Path -LiteralPath $llmConfigPath)) {
    if (Test-Path -LiteralPath $seedLlm) {
      Write-Host "[Learn2Earn] Loading demo LLM config..."
      Copy-Item -LiteralPath $seedLlm -Destination $llmConfigPath -Force
    } else {
      Write-Host "[Learn2Earn] WARNING: No demo LLM config found at $seedLlm. Configure providers in Settings before generating products."
    }
  }

  $storageEmpty = $true
  if (Test-Path -LiteralPath $storagePath) {
    $entryCount = (Get-ChildItem -LiteralPath $storagePath -Force -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($entryCount -gt 0) {
      $storageEmpty = $false
    }
  }
  if ($storageEmpty) {
    if (Test-Path -LiteralPath $seedStorageTar) {
      Write-Host "[Learn2Earn] Empty storage detected. Extracting demo storage..."
      if (-not (Test-Path -LiteralPath $storagePath)) {
        New-Item -ItemType Directory -Path $storagePath -Force | Out-Null
      }
      $tar = (Get-Command tar -ErrorAction SilentlyContinue)
      if ($tar) {
        Push-Location $projectRoot
        & tar -xzf $seedStorageTar -C $storagePath
        Pop-Location
        Write-Host "[Learn2Earn] Demo storage extracted."
      } else {
        Write-Host "[Learn2Earn] WARNING: tar not available. Run from Git Bash or install Windows 10+ tar to extract demo storage."
      }
    } else {
      Write-Host "[Learn2Earn] WARNING: No demo storage found at $seedStorageTar. Skill marketplace will be empty."
    }
  }
}

Initialize-SeedData

function Select-Python {
  param([switch]$RequirePrepared)
  $candidates = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    (Join-Path $projectRoot "work_verify_venv\Scripts\python.exe"),
    (Join-Path $projectRoot "backend\learn2earn\Scripts\python.exe")
  )
  foreach ($candidate in $candidates) {
    if ((Test-Path -LiteralPath $candidate) -and ((-not $RequirePrepared) -or (Test-PreparedEnvironment $candidate))) {
      return $candidate
    }
  }
  throw "No prepared Python virtual environment found. Run: first-time prepare script."
}

function Test-HttpReady {
  param([string]$TargetUrl)
  try {
    $response = Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 2
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
  } catch {
    return $false
  }
}

function Test-PortFree {
  param([int]$Port)
  $listener = $null
  try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), $Port)
    $listener.Start()
    return $true
  } catch {
    return $false
  } finally {
    if ($listener) {
      $listener.Stop()
    }
  }
}

function Stop-ProcessTree {
  param([int]$ProcessId)
  $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
  foreach ($child in $children) {
    Stop-ProcessTree -ProcessId $child.ProcessId
  }
  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Test-FrontendBuild {
  # 🔍 [作用] 校验 frontend\dist 是一份"完整可用"的构建产物，而不仅仅是 index.html 存在。
  # 🔍 [陷阱] 云同步盘（百度同步盘 / OneDrive）会出现只保留 index.html、把 assets\ 整个目录
  #          删掉的半同步状态。旧逻辑只判断 index.html 是否存在，于是误判"已就绪"，
  #          跳过重新构建直接起 uvicorn；而后端 main.py 里 /assets 挂载有
  #          `if assets_dir.exists()` 守卫，assets 不存在时挂载被跳过，
  #          /assets/index-xxx.js 落进 SPA 兜底路由被当成 index.html 返回，
  #          浏览器拿到 Content-Type: text/html 的 "JS 模块" 拒绝执行 → 整页白屏。
  #          表现就是"能启动但看不到任何界面"，极具迷惑性。
  # 🔍 [返回] $true = 构建产物完整；$false = 需要重新构建

  # 🔍 [语法] Join-Path 拼接路径，避免手写反斜杠在不同调用方下出错
  $indexPath = Join-Path $projectRoot "frontend\dist\index.html"
  # 🔍 [作用] 入口 HTML 不存在，说明压根没构建过
  # 🔍 [陷阱] 必须用 -LiteralPath，项目路径含中文与方括号时 -Path 会被当通配符解析
  if (-not (Test-Path -LiteralPath $indexPath)) {
    return $false
  }

  # 🔍 [作用] assets 目录整体缺失是最典型的半同步损坏形态，先快速短路判断
  $assetsDir = Join-Path $projectRoot "frontend\dist\assets"
  if (-not (Test-Path -LiteralPath $assetsDir)) {
    return $false
  }

  # 🔍 [语法] Get-Content -Raw 一次性读成单个字符串（不加 -Raw 会得到字符串数组）
  # 🔍 [作用] 读入 index.html 原文，准备提取其中引用的静态资源路径
  $html = Get-Content -LiteralPath $indexPath -Raw

  # 🔍 [语法] [regex]::Matches(输入, 模式) 返回全部匹配项集合
  # 🔍 [作用] 抓出形如 /assets/index-B9FWkzD4.js、/assets/index-Ci-OYN7S.css 的引用
  # 🔍 [陷阱] 字符类里必须包含 '-' 且放在末尾（或转义），否则会被解析成区间导致漏匹配；
  #          vite 生成的 hash 文件名里 '-' 是常客，例如 index-Ci-OYN7S.css
  $refs = [regex]::Matches($html, '/assets/[A-Za-z0-9._-]+')

  # 🔍 [作用] 一个引用都没抓到 → index.html 本身是残缺/被截断的，同样判为不可用
  if ($refs.Count -eq 0) {
    return $false
  }

  # 🔍 [作用] 逐个核对被引用的资源文件是否真实落盘，任意一个缺失即判定构建不完整
  foreach ($match in $refs) {
    # 🔍 [语法] TrimStart('/') 去掉开头斜杠；-replace 是正则替换，把 URL 斜杠转成 Windows 反斜杠
    # 🔍 [陷阱] -replace 第一个参数是正则，'/' 本身无特殊含义所以可直接用
    $relative = $match.Value.TrimStart('/') -replace '/', '\'
    $fullPath = Join-Path $projectRoot ("frontend\dist\" + $relative)
    if (-not (Test-Path -LiteralPath $fullPath)) {
      Write-Host "[Learn2Earn] Frontend build is incomplete: missing $($match.Value)"
      return $false
    }
  }

  # 🔍 [作用] 入口页 + 全部被引用资源都在，判定构建产物完整可用
  return $true
}

function Test-PreparedEnvironment {
  param([string]$PythonPath)
  # 🔍 [作用] 用完整性校验替换原来"只看 index.html 存在"的弱判断，
  #          让残缺 dist 能正确触发 Repair-PreparedEnvironment 自动重建
  if (-not (Test-FrontendBuild)) {
    return $false
  }
  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    & $PythonPath -c "import fastapi, uvicorn, sqlalchemy, pydantic, aiosqlite, httpx, docx, PIL, multipart" 2>&1 | Out-Null
    $importExitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }
  return ($importExitCode -eq 0)
}

function Repair-PreparedEnvironment {
  Write-Host "[Learn2Earn] Dependencies or frontend build are missing/outdated."
  Write-Host "[Learn2Earn] Running one-time preparation automatically..."
  & (Join-Path $PSScriptRoot "prepare_local_demo_once.ps1")
  if ($LASTEXITCODE -ne 0) {
    throw "Automatic preparation failed. Run the first-time prepare script and review its error output."
  }
}

$python = Select-Python
if (-not (Test-PreparedEnvironment $python)) {
  Repair-PreparedEnvironment
  $python = Select-Python -RequirePrepared
  if (-not (Test-PreparedEnvironment $python)) {
    throw "Preparation completed, but required dependencies or frontend build are still unavailable."
  }
}

# Reload current source instead of reusing a project process that may still
# serve routes and frontend assets from an earlier branch or commit.
if (Test-Path -LiteralPath $pidFile) {
  $recordedPid = [int](Get-Content -LiteralPath $pidFile -Raw)
  $recordedProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$recordedPid" -ErrorAction SilentlyContinue
  if ($recordedProcess -and $recordedProcess.CommandLine -match 'uvicorn\s+backend\.app\.main:app') {
    Write-Host "[Learn2Earn] Restarting the existing local server to load current code..."
    Stop-ProcessTree -ProcessId $recordedPid
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
  }
}

$port = $null
foreach ($candidate in 9000..9010) {
  $candidateUrl = "http://127.0.0.1:$candidate/"
  $candidateHealthUrl = "http://127.0.0.1:$candidate/api/health"
  if (Test-HttpReady $candidateHealthUrl) {
    Write-Host "[Learn2Earn] Server is already running: $candidateUrl"
    Write-Host "[Learn2Earn] Opening it in your browser..."
    Set-Content -LiteralPath $urlFile -Encoding ASCII -Value $candidateUrl
    if (-not $NoBrowser) {
      [System.Diagnostics.Process]::Start($candidateUrl) | Out-Null
    }
    Write-Host ""
    Write-Host "[Learn2Earn] The running server is unaffected. Close this window any time."
    Read-Host -Prompt "[Learn2Earn] Press ENTER to close this window"
    return
  }
  if (Test-PortFree $candidate) {
    $port = $candidate
    break
  }
}

if (-not $port) {
  throw "Ports 9000-9010 are all occupied. Stop another service or edit this script to use a different port."
}

$url = "http://127.0.0.1:$port/"
$healthUrl = "http://127.0.0.1:$port/api/health"

Write-Host "[Learn2Earn] Starting local server in this window: $url"
Write-Host "[Learn2Earn] Log file: $logFile"
Write-Host "[Learn2Earn] The server runs in the FOREGROUND, so this window stays open while it runs."
Write-Host "[Learn2Earn] Stop it by closing this window (Ctrl+C) or by running the Stop script."
Write-Host ""

if (Test-Path -LiteralPath $logFile) {
  Remove-Item -LiteralPath $logFile -Force
}
if (Test-Path -LiteralPath $errLogFile) {
  Remove-Item -LiteralPath $errLogFile -Force
}

Set-Content -LiteralPath $urlFile -Encoding ASCII -Value $url

$serverProcess = $null
try {
  # [Why base Python + PYTHONPATH] The `.venv\Scripts\python.exe` launcher re-executes the
  # base interpreter from `pyvenv.cfg`'s `home`. When uvicorn (or any library that uses
  # multiprocessing.spawn under the hood) launches a child, the child loses the venv's
  # site-packages and falls back to the base interpreter's packages, causing version
  # mismatches and SQLite "unable to open database file" errors. We bypass the venv launcher
  # and run the base interpreter directly, explicitly prepending the venv site-packages
  # via PYTHONPATH.
  $pyvenvCfg = Get-Content -LiteralPath "$projectRoot\.venv\pyvenv.cfg" -Encoding ASCII
  $baseHome = $null
  foreach ($line in $pyvenvCfg) {
    if ($line -match '^home\s*=\s*(.+)') {
      $baseHome = $Matches[1].Trim()
      break
    }
  }
  if (-not $baseHome) { $baseHome = Split-Path -Parent (Get-Command python.exe -ErrorAction SilentlyContinue).Source }
  $basePython = ($baseHome -replace '\$','') + '\python.exe'

  $startInfo = New-Object System.Diagnostics.ProcessStartInfo
  $startInfo.FileName = $basePython
  $startInfo.Arguments = "-m uvicorn backend.app.main:app --host 127.0.0.1 --port $port --log-level info"
  $startInfo.WorkingDirectory = $projectRoot
  $startInfo.UseShellExecute = $false
  $startInfo.EnvironmentVariables.Remove('PYTHONPATH') | Out-Null
  $startInfo.EnvironmentVariables['PYTHONPATH'] = "$projectRoot\.venv\Lib\site-packages"
  $startInfo.EnvironmentVariables["LEARN2EARN_DATABASE_PATH"] = [string]$env:LEARN2EARN_DATABASE_PATH
  $startInfo.CreateNoWindow = $true
  $serverProcess = [System.Diagnostics.Process]::Start($startInfo)
  if (-not $serverProcess) {
    throw "Python server process could not be created."
  }
  Set-Content -LiteralPath $pidFile -Encoding ASCII -Value $serverProcess.Id

  $ready = $false
  $deadline = [DateTime]::UtcNow.AddSeconds(30)
  while ([DateTime]::UtcNow -lt $deadline -and -not $serverProcess.HasExited) {
    if (Test-HttpReady $healthUrl) {
      $ready = $true
      break
    }
    Start-Sleep -Milliseconds 250
  }
  if (-not $ready) {
    $exitDetail = if ($serverProcess.HasExited) { " Exit code: $($serverProcess.ExitCode)." } else { "" }
    throw "Server did not become ready within 30 seconds.$exitDetail"
  }

  Write-Host "[Learn2Earn] Server is ready: $url" -ForegroundColor Green
  if (-not $NoBrowser) {
    [System.Diagnostics.Process]::Start($url) | Out-Null
  }
  Write-Host "[Learn2Earn] Keep this window open. Press Ctrl+C or run the stop script to stop."
  while (-not $serverProcess.HasExited) {
    Start-Sleep -Seconds 1
  }
  Write-Host "[Learn2Earn] Server process exited with code $($serverProcess.ExitCode)."
} catch {
  $message = "[Learn2Earn] Startup failed: $($_.Exception.Message)"
  Write-Host $message -ForegroundColor Red
  Set-Content -LiteralPath $errLogFile -Encoding UTF8 -Value $message
  exit 1
} finally {
  if ($serverProcess -and -not $serverProcess.HasExited) {
    $serverProcess.Kill()
    $serverProcess.WaitForExit()
  }
  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
  Write-Host ""
  Write-Host "[Learn2Earn] Server stopped."
}
