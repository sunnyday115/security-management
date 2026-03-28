"""セキュリティマネジメント試験 学習アプリ"""

import os
import sqlite3

import markdown
from markupsafe import Markup
from flask import Flask, g, render_template, request, redirect, url_for, flash

# --- DB設定 ---
# DATABASE_URL が設定されていれば PostgreSQL、なければ SQLite を使う
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Render は postgres:// 形式で提供するが、psycopg2 は postgresql:// が必要
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

BASE_DIR = os.path.dirname(__file__)
DATABASE_PATH = os.path.join(BASE_DIR, "..", "data", "learning.db")
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "..", "templates"),
    static_folder=os.path.join(BASE_DIR, "..", "static"),
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


@app.template_filter("md")
def markdown_filter(text: str) -> Markup:
    """Markdown文字列をHTMLに変換するJinja2フィルター"""
    html = markdown.markdown(text, extensions=["tables", "fenced_code"])
    return Markup(html)


# ========== DB接続ラッパー ==========
class DbWrapper:
    """SQLite と PostgreSQL の差異を吸収するラッパー

    - プレースホルダー: SQLite の ? を PostgreSQL の %s に自動変換
    - 行アクセス: どちらも row["カラム名"] でアクセス可能
    """

    def __init__(self, conn, use_postgres: bool = False):
        self._conn = conn
        self._use_postgres = use_postgres

    def execute(self, sql: str, params=()):
        """SQLを実行してカーソルを返す"""
        if self._use_postgres:
            sql = sql.replace("?", "%s")
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return cur
        return self._conn.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


# ========== データベース接続 ==========
def get_db() -> DbWrapper:
    """リクエストごとにDB接続を取得する"""
    if "db" not in g:
        if USE_POSTGRES:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        else:
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
        g.db = DbWrapper(conn, USE_POSTGRES)
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """リクエスト終了時にDB接続を閉じる"""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """スキーマとシードデータでDBを初期化する"""
    if USE_POSTGRES:
        schema_path = os.path.join(DATA_DIR, "schema_pg.sql")
        seed_path = os.path.join(DATA_DIR, "seed_pg.sql")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        with open(schema_path, encoding="utf-8") as f:
            cur.execute(f.read())
        with open(seed_path, encoding="utf-8") as f:
            cur.execute(f.read())
        conn.commit()
        conn.close()
    else:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        with open(os.path.join(DATA_DIR, "schema.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())
        # シードデータ投入時は外部キー制約を一時的に無効化（投入順序の制約回避）
        with open(os.path.join(DATA_DIR, "seed.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


# ========== ルート: トップページ ==========
@app.route("/")
def index():
    """トップページ: 分野一覧と正答率を表示"""
    db = get_db()
    # 分野一覧を取得
    categories = db.execute(
        "SELECT * FROM categories ORDER BY sort_order"
    ).fetchall()

    # 分野ごとの正答率を計算
    stats = {}
    for cat in categories:
        row = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM quiz_history
            WHERE question_id IN (
                SELECT id FROM questions WHERE category_id = ?
            )
            """,
            (cat["id"],),
        ).fetchone()
        total = row["total"]
        correct = row["correct"] or 0
        stats[cat["id"]] = {
            "total": total,
            "correct": correct,
            "rate": round(correct / total * 100) if total > 0 else None,
        }

    return render_template("index.html", categories=categories, stats=stats)


# ========== ルート: ○×クイズ ==========
@app.route("/quiz/<int:category_id>")
def quiz(category_id: int):
    """指定分野からランダムに1問出題する"""
    db = get_db()
    category = db.execute(
        "SELECT * FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if category is None:
        flash("指定された分野が見つかりません。", "error")
        return redirect(url_for("index"))

    question = db.execute(
        """
        SELECT * FROM questions
        WHERE category_id = ?
        ORDER BY RANDOM()
        LIMIT 1
        """,
        (category_id,),
    ).fetchone()

    if question is None:
        flash("この分野にはまだ問題がありません。", "error")
        return redirect(url_for("index"))

    return render_template("quiz.html", category=category, question=question)


@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    """回答を受け取り、正誤判定して結果を表示する"""
    db = get_db()
    question_id = int(request.form["question_id"])
    user_answer = request.form["answer"] == "true"

    question = db.execute(
        "SELECT * FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    category = db.execute(
        "SELECT * FROM categories WHERE id = ?", (question["category_id"],)
    ).fetchone()

    is_correct = user_answer == bool(question["correct_answer"])

    # 履歴を保存
    db.execute(
        "INSERT INTO quiz_history (question_id, is_correct) VALUES (?, ?)",
        (question_id, int(is_correct)),
    )
    db.commit()

    # 関連するまとめノートを取得（問題ごとに紐付けられたノートを優先）
    related_note = None
    if question["related_note_id"]:
        related_note = db.execute(
            "SELECT * FROM notes WHERE id = ?",
            (question["related_note_id"],),
        ).fetchone()
    # related_note_id が未設定の場合はカテゴリの先頭ノートをフォールバック
    if not related_note:
        related_note = db.execute(
            "SELECT * FROM notes WHERE category_id = ? ORDER BY id LIMIT 1",
            (question["category_id"],),
        ).fetchone()

    return render_template(
        "quiz_result.html",
        category=category,
        question=question,
        user_answer=user_answer,
        is_correct=is_correct,
        related_note=related_note,
    )


# ========== ルート: まとめノート ==========
@app.route("/notes")
def notes_list():
    """まとめノート一覧"""
    db = get_db()
    notes = db.execute(
        """
        SELECT notes.*, categories.name AS category_name
        FROM notes
        JOIN categories ON notes.category_id = categories.id
        ORDER BY categories.sort_order
        """
    ).fetchall()
    return render_template("notes_list.html", notes=notes)


@app.route("/notes/<int:note_id>")
def note_detail(note_id: int):
    """まとめノート詳細"""
    db = get_db()
    note = db.execute(
        """
        SELECT notes.*, categories.name AS category_name
        FROM notes
        JOIN categories ON notes.category_id = categories.id
        WHERE notes.id = ?
        """,
        (note_id,),
    ).fetchone()
    if note is None:
        flash("指定されたノートが見つかりません。", "error")
        return redirect(url_for("notes_list"))
    return render_template("note_detail.html", note=note)


# ========== ルート: 問題管理 ==========
@app.route("/manage")
def manage():
    """問題・ノート管理画面"""
    db = get_db()
    categories = db.execute(
        "SELECT * FROM categories ORDER BY sort_order"
    ).fetchall()
    questions = db.execute(
        """
        SELECT questions.*, categories.name AS category_name
        FROM questions
        JOIN categories ON questions.category_id = categories.id
        ORDER BY categories.sort_order, questions.id
        """
    ).fetchall()
    notes = db.execute(
        """
        SELECT notes.*, categories.name AS category_name
        FROM notes
        JOIN categories ON notes.category_id = categories.id
        ORDER BY categories.sort_order
        """
    ).fetchall()
    return render_template(
        "manage.html", categories=categories, questions=questions, notes=notes
    )


@app.route("/manage/question/add", methods=["POST"])
def add_question():
    """○×問題を追加する"""
    db = get_db()
    category_id = int(request.form["category_id"])
    statement = request.form["statement"].strip()
    correct_answer = int(request.form["correct_answer"])
    explanation = request.form["explanation"].strip()
    related_note_id = request.form.get("related_note_id")
    related_note_id = int(related_note_id) if related_note_id else None

    if not statement:
        flash("問題文を入力してください。", "error")
        return redirect(url_for("manage"))

    db.execute(
        """
        INSERT INTO questions (category_id, statement, correct_answer, explanation, related_note_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (category_id, statement, correct_answer, explanation, related_note_id),
    )
    db.commit()
    flash("問題を追加しました。", "success")
    return redirect(url_for("manage"))


@app.route("/manage/question/edit/<int:question_id>", methods=["GET", "POST"])
def edit_question(question_id: int):
    """○×問題を編集する"""
    db = get_db()
    if request.method == "POST":
        category_id = int(request.form["category_id"])
        statement = request.form["statement"].strip()
        correct_answer = int(request.form["correct_answer"])
        explanation = request.form["explanation"].strip()
        related_note_id = request.form.get("related_note_id")
        related_note_id = int(related_note_id) if related_note_id else None
        if not statement:
            flash("問題文を入力してください。", "error")
            return redirect(url_for("edit_question", question_id=question_id))
        db.execute(
            """
            UPDATE questions
            SET category_id = ?, statement = ?, correct_answer = ?, explanation = ?,
                related_note_id = ?
            WHERE id = ?
            """,
            (category_id, statement, correct_answer, explanation, related_note_id, question_id),
        )
        db.commit()
        flash("問題を更新しました。", "success")
        return redirect(url_for("manage"))

    question = db.execute(
        "SELECT * FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    if question is None:
        flash("指定された問題が見つかりません。", "error")
        return redirect(url_for("manage"))
    categories = db.execute(
        "SELECT * FROM categories ORDER BY sort_order"
    ).fetchall()
    notes = db.execute(
        """
        SELECT notes.*, categories.name AS category_name
        FROM notes
        JOIN categories ON notes.category_id = categories.id
        ORDER BY categories.sort_order, notes.id
        """
    ).fetchall()
    return render_template(
        "edit_question.html", question=question, categories=categories, notes=notes
    )


@app.route("/manage/question/delete/<int:question_id>", methods=["POST"])
def delete_question(question_id: int):
    """問題を削除する"""
    db = get_db()
    db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    db.commit()
    flash("問題を削除しました。", "success")
    return redirect(url_for("manage"))


@app.route("/manage/note/add", methods=["POST"])
def add_note():
    """まとめノートを追加する"""
    db = get_db()
    category_id = int(request.form["category_id"])
    title = request.form["title"].strip()
    content = request.form["content"].strip()

    if not title or not content:
        flash("タイトルと内容を入力してください。", "error")
        return redirect(url_for("manage"))

    db.execute(
        "INSERT INTO notes (category_id, title, content) VALUES (?, ?, ?)",
        (category_id, title, content),
    )
    db.commit()
    flash("ノートを追加しました。", "success")
    return redirect(url_for("manage"))


@app.route("/manage/note/edit/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id: int):
    """まとめノートを編集する"""
    db = get_db()
    if request.method == "POST":
        category_id = int(request.form["category_id"])
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        if not title or not content:
            flash("タイトルと内容を入力してください。", "error")
            return redirect(url_for("edit_note", note_id=note_id))
        db.execute(
            "UPDATE notes SET category_id = ?, title = ?, content = ? WHERE id = ?",
            (category_id, title, content, note_id),
        )
        db.commit()
        flash("ノートを更新しました。", "success")
        return redirect(url_for("manage"))

    note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if note is None:
        flash("指定されたノートが見つかりません。", "error")
        return redirect(url_for("manage"))
    categories = db.execute(
        "SELECT * FROM categories ORDER BY sort_order"
    ).fetchall()
    return render_template("edit_note.html", note=note, categories=categories)


@app.route("/manage/note/delete/<int:note_id>", methods=["POST"])
def delete_note(note_id: int):
    """ノートを削除する"""
    db = get_db()
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    flash("ノートを削除しました。", "success")
    return redirect(url_for("manage"))


# ========== エントリーポイント ==========
if __name__ == "__main__":
    if USE_POSTGRES:
        print("PostgreSQL モードで起動します...")
    else:
        if not os.path.exists(DATABASE_PATH):
            print("データベースを初期化しています...")
            init_db()
            print("初期化完了。")
    app.run(debug=True, port=5000)
