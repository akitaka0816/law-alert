# deploy.ps1 — index.html と history.json を GitHub にプッシュする
# 前提: git init & git remote add origin が完了していること

Set-Location $PSScriptRoot

# 未追跡ファイルを追加（Pages で参照する静的ファイル）
git add index.html history.json watchlist.json

# 差分がなければスキップ
$status = git status --porcelain
if (-not $status) {
    Write-Host "変更なし。プッシュをスキップします。"
    exit 0
}

$date = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "update: $date"
git push origin main

Write-Host ""
Write-Host "GitHub Pages に公開しました。"
Write-Host "数分後に以下のURLで確認できます:"
$remote = git remote get-url origin 2>$null
if ($remote -match "github\.com[:/](.+?)(?:\.git)?$") {
    $repo = $Matches[1]
    $parts = $repo -split "/"
    if ($parts.Count -ge 2) {
        Write-Host "  https://$($parts[0]).github.io/$($parts[1])/"
    }
}
