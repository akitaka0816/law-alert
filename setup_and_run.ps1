# Law Alert setup + run (Windows PowerShell)
$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $baseDir ".venv"
$reqPath = Join-Path $baseDir "requirements.txt"
$monitorPath = Join-Path $baseDir "monitor.py"
$activateScript = Join-Path $venvDir "Scripts\\Activate.ps1"

Write-Host "== python env check =="
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "pythonが見つからないため、py を使います。"
  } else {
    throw "python も py も見つかりません。Pythonをインストールしてください。"
  }
}

if (-not (Test-Path $venvDir)) {
  Write-Host "== creating venv =="
  if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m venv $venvDir
  } else {
    py -m venv $venvDir
  }
}

Write-Host "== installing dependencies =="
& $activateScript | Out-Null

python -m pip install --upgrade pip
python -m pip install -r $reqPath

Write-Host "== running monitor (test) =="
python $monitorPath

Write-Host "Done."

