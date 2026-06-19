"""话术数据库管理器 - 安全版"""
import sqlite3
import json
import random
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts.db")
JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts.json")


def _get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化话术数据库（幂等，不重复创建）"""
    if os.path.exists(DB_PATH):
        conn = _get_conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM scripts").fetchone()[0]
            if count > 0:
                print(f"话术数据库已存在，共 {count} 条话术")
                return
        except Exception:
            pass
        finally:
            conn.close()

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                subcategory TEXT,
                content TEXT NOT NULL,
                emotion TEXT,
                weight INTEGER DEFAULT 1
            )
        """)

        def insert_items(category, items, subcategory=None, emotion=None):
            if isinstance(items, list):
                for item in items:
                    cur.execute(
                        "INSERT INTO scripts (category, subcategory, content, emotion) VALUES (?, ?, ?, ?)",
                        (category, subcategory, item, emotion)
                    )
            elif isinstance(items, dict):
                for key, val in items.items():
                    insert_items(category, val, subcategory=key)

        for cat, val in data.items():
            if cat in ("character",):
                continue
            if isinstance(val, dict):
                for sub, items in val.items():
                    if isinstance(items, list):
                        for item in items:
                            cur.execute(
                                "INSERT INTO scripts (category, subcategory, content) VALUES (?, ?, ?)",
                                (cat, sub, item)
                            )
                    elif isinstance(items, dict):
                        for emotion, phrases in items.items():
                            for p in phrases:
                                cur.execute(
                                    "INSERT INTO scripts (category, subcategory, content, emotion) VALUES (?, ?, ?, ?)",
                                    (cat, sub, p, emotion)
                                )
            elif isinstance(val, list):
                for item in val:
                    cur.execute(
                        "INSERT INTO scripts (category, content) VALUES (?, ?)",
                        (cat, item)
                    )

        conn.commit()

        total = cur.execute("SELECT COUNT(*) FROM scripts").fetchone()[0]
        cats = cur.execute("SELECT category, COUNT(*) FROM scripts GROUP BY category").fetchall()
        print(f"话术数据库初始化完成！共 {total} 条话术")
        for cat, count in cats:
            print(f"  - {cat}: {count} 条")
    finally:
        conn.close()


def get_random(category, subcategory=None, emotion=None):
    """随机获取话术"""
    if not os.path.exists(DB_PATH):
        init_db()

    conn = _get_conn()
    try:
        query = "SELECT content FROM scripts WHERE category = ?"
        params = [category]

        if subcategory:
            query += " AND subcategory = ?"
            params.append(subcategory)

        if emotion:
            query += " AND (emotion = ? OR emotion IS NULL)"
            params.append(emotion)

        rows = conn.execute(query, params).fetchall()
        if rows:
            return random.choice(rows)[0]
        return None
    finally:
        conn.close()


def search(keyword):
    """搜索话术"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT category, subcategory, content FROM scripts WHERE content LIKE ?",
            (f"%{keyword}%",)
        ).fetchall()
        return rows
    finally:
        conn.close()


def get_all_categories():
    """获取所有分类"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT category, subcategory, COUNT(*) FROM scripts GROUP BY category, subcategory"
        ).fetchall()
        return rows
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("\n=== 测试随机获取 ===")
    for cat in ["greetings", "emotional_responses", "small_talk", "flirty", "caring"]:
        script = get_random(cat)
        print(f"{cat}: {script}")
