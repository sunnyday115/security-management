-- セキュリティマネジメント学習アプリ: データベーススキーマ

-- 分野マスター
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- 分野名
    description TEXT,             -- 分野の説明
    sort_order INTEGER NOT NULL   -- 表示順
);

-- ○×問題
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    statement TEXT NOT NULL,        -- 問題文
    correct_answer INTEGER NOT NULL CHECK (correct_answer IN (0, 1)),  -- 正解: 1=○, 0=×
    explanation TEXT,               -- 解説
    related_note_id INTEGER,        -- 関連するまとめノートのID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (related_note_id) REFERENCES notes(id)
);

-- まとめノート
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    title TEXT NOT NULL,            -- ノートのタイトル
    content TEXT NOT NULL,          -- ノートの本文
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- 学習履歴
CREATE TABLE IF NOT EXISTS quiz_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),  -- 1=正解, 0=不正解
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
