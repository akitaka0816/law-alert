## 目的

官庁・行政サイトの更新（法令改正/官報/パブコメ等）を毎日チェックし、**更新があれば/なければ** Windowsのトースト通知を出します。

## 対象ソース（初期設定）

- `e-Gov パブリックコメント（RSS）`（全件）
- `厚労省 新着/緊急（RSS）`
- `官報（RSS）`
- `e-Gov 法令検索 更新法令一覧`（HTML差分）

ソースとキーワードは `config.json` で変更できます。

## セットアップ（初回だけ）

PowerShell を開いてこのフォルダで実行：

```powershell
cd "C:\Users\akita\OneDrive\ドキュメント\仕事\law-alert"
.\setup_and_run.ps1
```

（`setup_and_run.ps1` が `venv` 作成、依存関係のインストール、`monitor.py` のテスト実行までやってくれます）

動作確認：

```powershell
python .\monitor.py
```

## 毎日10時に自動実行（Windows タスク スケジューラ）

### スクリプトで作る（簡単）

```powershell
cd "C:\Users\akita\OneDrive\ドキュメント\仕事\law-alert"
.\register_task.ps1
```

もし手動で作りたい場合は、従来通りGUI手順でもOKです。

### コマンドで作る（任意）

```powershell
$taskName = "LawAlertDaily10"
$pythonw  = "C:\Users\akita\OneDrive\ドキュメント\仕事\law-alert\.venv\Scripts\pythonw.exe"
$script   = "C:\Users\akita\OneDrive\ドキュメント\仕事\law-alert\monitor.py"

schtasks /Create /F /TN $taskName /SC DAILY /ST 10:00 /TR "`"$pythonw`" `"$script`""
```

## 設定

- `config.json`
  - `keywords`: タイトル/リンク/更新情報にこのキーワードが含まれると「重要そうな更新」として通知
  - `notify_on_no_updates`: 更新がなくても通知（要件に合わせて true）

## 仕組み（ざっくり）

- 各ソースから最新N件を取得
- `state.json` に「前回までに見たID」を保存
- 新規IDがあれば「更新」として通知
- キーワードに当たれば「重要そう」として通知
- 新規が無ければ「更新なし」を通知（設定でON/OFF）
