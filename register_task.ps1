# Law Alert scheduled task registration (Windows PowerShell)
$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $baseDir ".venv"
$monitorPath = Join-Path $baseDir "monitor.py"

$taskName = "LawAlertDaily10"
$startDir = $baseDir

# まずは python.exe を優先（失敗時に原因を追いやすい）。
$pythonExe = Join-Path $venvDir "Scripts\\python.exe"
$runner = $pythonExe
if (-not (Test-Path $runner)) {
  $pythonw = Join-Path $venvDir "Scripts\\pythonw.exe"
  $runner = $pythonw
}

if (-not (Test-Path $runner)) {
  throw "venv内のpython実行ファイルが見つかりません。先に setup_and_run.ps1 を実行して下さい。"
}

$tr = "`"$runner`" `"$monitorPath`""

Write-Host "Creating scheduled task: $taskName"
schtasks /Create /F /TN $taskName /SC DAILY /ST 10:00 /TR $tr /RL LIMITED /SD (Get-Date).Date.ToString("yyyy-MM-dd") | Out-Null

Write-Host "Done. Task Schedulerで確認してください。"

