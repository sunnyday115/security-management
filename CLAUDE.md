# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

情報セキュリティマネジメント試験の学習用Webアプリ（自分専用）。
○×クイズとまとめノートで、公式シラバスに沿った分野別学習ができる。
クイズの解説画面では、同じ分野のまとめノートへのリンクが自動で表示される。

## コマンド

```bash
# アプリ起動（初回はDBも自動初期化される）
python src/app.py

# ブラウザで http://127.0.0.1:5000 にアクセス

# DBを再初期化したい場合（data/learning.db を削除して再起動）
rm data/learning.db && python src/app.py
```

## アーキテクチャ

- **フレームワーク**: Flask + HTML/CSS（Jinja2テンプレート）
- **データベース**: SQLite（`data/learning.db`）
- **Pythonバージョン**: 3.13（`C:\Users\sunny\AppData\Local\Programs\Python\Python313\python.exe`）

### ファイル構成

```
src/app.py          … Flaskアプリ本体（全ルート定義・DB接続）
data/schema.sql     … テーブル定義（categories, questions, notes, quiz_history）
data/seed.sql       … 初期サンプルデータ
data/learning.db    … SQLiteデータベース（自動生成・.gitignore対象）
templates/          … Jinja2テンプレート（base.html を継承）
static/style.css    … スタイルシート
```

### データモデルの関係

- `categories`（分野）を中心に、`questions`（○×問題）と `notes`（まとめノート）が紐づく
- クイズ解説→まとめノートの連動は `category_id` で実現
- `quiz_history` に回答履歴を記録し、分野別正答率を算出

### 画面構成

1. **トップページ** (`/`) — 分野一覧 + 正答率 + クイズ開始リンク
2. **○×クイズ** (`/quiz/<id>`) — ランダム出題 → 回答 → 解説 + 関連ノートリンク
3. **まとめノート** (`/notes`, `/notes/<id>`) — 分野別の学習テキスト
4. **問題管理** (`/manage`) — 問題・ノートの追加・削除
