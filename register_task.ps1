# Law Alert scheduled task registration (Windows PowerShell)
$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$taskName = "LawAlertDaily10"
$wrapperPath = Join-Path $baseDir "run_and_deploy.ps1"

if (-not (Test-Path $wrapperPath)) {
  throw "run_and_deploy.ps1 が見つかりません。"
}

# powershell.exe で run_and_deploy.ps1 を実行する
$psExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$tr = "`"$psExe`" -NoProfile -ExecutionPolicy Bypass -File `"$wrapperPath`""

Write-Host "Creating scheduled task: $taskName"
schtasks /Create /F /TN $taskName /SC DAILY /ST 10:00 /TR $tr /RL LIMITED /SD (Get-Date).Date.ToString("yyyy-MM-dd") | Out-Null

Write-Host "Done. 毎朝10時に monitor.py 実行 → GitHub Pages 自動更新されます。"

