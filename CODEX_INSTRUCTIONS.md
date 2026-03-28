# Codex への引き継ぎ指示書

## プロジェクト概要

情報セキュリティマネジメント試験の学習用Webアプリ（自分専用）。
Flask + HTML/CSS + SQLite で構成。○×クイズとまとめノートで学習する。

## 現在の状態

アプリの基本実装は完了済み。以下のファイルが存在する：

```
src/app.py             … Flaskアプリ本体
data/schema.sql        … DBスキーマ定義
data/seed.sql          … 初期データ（問題73問＋ノート12本に拡充済み）
data/learning.db       … SQLiteデータベース（古いまま。再生成が必要）
templates/             … Jinja2テンプレート（8ファイル）
static/style.css       … スタイルシート
requirements.txt       … Flask==3.1.0, Markdown==3.7
```

## やってほしいこと

### 1. DBの再初期化と動作確認

`data/learning.db` を削除してからアプリを起動し、全画面が正常に動作するか確認する。

```bash
rm data/learning.db
python src/app.py
```

確認すべきURL：
- `http://127.0.0.1:5000/` — トップページ（6分野の一覧と正答率）
- `http://127.0.0.1:5000/quiz/1` — ○×クイズ
- `http://127.0.0.1:5000/quiz/answer` — POST で回答送信 → 結果画面に関連ノートが本文ごと表示されること
- `http://127.0.0.1:5000/notes` — まとめノート一覧
- `http://127.0.0.1:5000/notes/1` — ノート詳細（Markdownが正しくHTMLに変換されていること）
- `http://127.0.0.1:5000/manage` — 問題管理画面（編集・削除ボタンがあること）
- `http://127.0.0.1:5000/manage/question/edit/1` — 問題編集画面
- `http://127.0.0.1:5000/manage/note/edit/1` — ノート編集画面

### 2. 不具合があれば修正

特に以下の点を確認：
- `seed.sql` のINSERT文にSQL構文エラーがないか（シングルクォートのエスケープ漏れ等）
- 問題編集・ノート編集の画面遷移とDB更新が正しく動作するか
- クイズ結果画面で同一分野の複数ノートが全て表示されるか（`related_notes` がリストで渡されている）

### 3. CLAUDE.md の更新

動作確認完了後、`CLAUDE.md` の内容を現在のプロジェクト状態に合わせて更新する。
特に以下の情報を反映：
- 問題数とノート数の最新値
- 編集機能が追加されたこと
- Markdown記法対応（markdownライブラリ使用）

## 技術的な補足

- Python: 3.13（パス: `C:\Users\sunny\AppData\Local\Programs\Python\Python313\python.exe`）
- Markdown変換: `app.py` で `@app.template_filter("md")` としてJinja2フィルターを登録済み。テンプレートでは `{{ note.content | md }}` で使用
- クイズ↔ノート連動: `category_id`（分野ID）で紐付け。クイズ結果画面に同じ分野のノート本文を全て表示する仕様

## コーディングルール

- コメント・docstring は日本語
- Python の命名規則: 関数・変数は snake_case、クラスは PascalCase、定数は UPPER_SNAKE_CASE
- 確認なしにファイルの削除や大規模な変更をしないこと
- `.env` やAPIキー・パスワードをコミットしないこと
