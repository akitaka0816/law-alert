# run_and_deploy.ps1 — monitor.py を実行してから GitHub にプッシュする

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $python)) {
    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}

# 1. 法改正情報を取得 & index.html を生成
& $python (Join-Path $PSScriptRoot "monitor.py")

# 2. GitHub にプッシュ
& (Join-Path $PSScriptRoot "deploy.ps1")
