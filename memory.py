"""记忆模块 - 性能优化版"""
import sqlite3
import time
from typing import List, Tuple

_db_path = None
_tables_created = False


def _get_db_path():
    global _db_path
    if _db_path is None:
        from config import DB_PATH
        _db_path = DB_PATH
    return _db_path


def _get_conn():
    """获取数据库连接"""
    global _tables_created
    conn = sqlite3.connect(_get_db_path(), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    if not _tables_created:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                time INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                summary TEXT,
                created_at INTEGER,
                last_chat INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_user ON chat(user_id, time)")
        conn.commit()
        _tables_created = True

    return conn


def save_message(user_id: str, role: str, content: str):
    """保存消息"""
    content = content[:2000] if content else ""
    now = int(time.time())
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO chat (user_id, role, content, time) VALUES (?, ?, ?, ?)",
            (user_id, role, content, now)
        )
        conn.execute("""
            INSERT INTO user_profile (user_id, last_chat) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_chat = ?
        """, (user_id, now, now))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def get_history(user_id: str, limit: int = 0) -> List[Tuple[str, str]]:
    """获取对话历史（limit=0 表示无限制）"""
    conn = _get_conn()
    try:
        if limit > 0:
            rows = conn.execute(
                "SELECT role, content FROM chat WHERE user_id = ? ORDER BY time DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT role, content FROM chat WHERE user_id = ? ORDER BY time DESC",
                (user_id,)
            ).fetchall()
        return rows[::-1]
    finally:
        conn.close()


def get_user_summary(user_id: str) -> str:
    """获取用户摘要"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT summary FROM user_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0] if row and row[0] else ""
    finally:
        conn.close()


def save_user_summary(user_id: str, summary: str):
    """保存用户摘要"""
    summary = summary[:2000] if summary else ""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO user_profile (user_id, summary) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET summary = ?
        """, (user_id, summary, summary))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def get_message_count(user_id: str) -> int:
    """获取消息数量"""
    conn = _get_conn()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM chat WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def get_recent_messages(user_id: str, limit: int = 5) -> List[Tuple[str, str]]:
    """获取最近消息"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content FROM chat WHERE user_id = ? ORDER BY time DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return rows[::-1]
    finally:
        conn.close()


def cleanup_old_messages(days: int = 90):
    """清理旧消息"""
    cutoff = int(time.time()) - (days * 86400)
    conn = _get_conn()
    try:
        deleted = conn.execute("DELETE FROM chat WHERE time < ?", (cutoff,)).rowcount
        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        return 0
    finally:
        conn.close()


def get_user_info(user_id: str) -> dict:
    """获取用户完整信息"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT name, summary, created_at, last_chat FROM user_profile WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return {
                "name": row[0] or "",
                "summary": row[1] or "",
                "created_at": row[2],
                "last_chat": row[3]
            }
        return {}
    finally:
        conn.close()
