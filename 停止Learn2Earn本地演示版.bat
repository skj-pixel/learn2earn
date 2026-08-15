@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$found=$false; foreach($p in 9000..9010){ try{ $cs=Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue; foreach($c in $cs){ $pr=Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue; if($pr){ Stop-Process -Id $pr.Id -Force; Write-Host ('[Learn2Earn] Stopped server on port '+$p+' (PID '+$pr.Id+')'); $found=$true } } }catch{} }; if(-not $found){ Write-Host '[Learn2Earn] No running server found on ports 9000-9010.' }; Remove-Item -LiteralPath (Join-Path (Get-Location) 'learn2earn_local_server.pid') -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath (Join-Path (Get-Location) 'learn2earn_local_server.url') -Force -ErrorAction SilentlyContinue"

pause
endlocal
