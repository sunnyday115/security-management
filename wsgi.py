"""PythonAnywhere 用 WSGI エントリーポイント"""

import os
import sys

# PythonAnywhere 上のプロジェクトパスを追加
# （デプロイ時に実際のパスに書き換える）
project_path = "/home/YOUR_USERNAME/security-management"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# src/ ディレクトリもパスに追加
src_path = os.path.join(project_path, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.app import app as application  # noqa: E402

# DBが存在しなければ初期化
from src.app import DATABASE_PATH, init_db  # noqa: E402

if not os.path.exists(DATABASE_PATH):
    init_db()
