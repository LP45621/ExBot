"""人类化记忆系统 - 带遗忘曲线和强化机制"""
import math
import time
import json
import sqlite3
import os
from typing import List, Dict, Optional


class HumanLikeMemory:
    """
    记忆 = 重要性 × 时间衰减 × 检索相关性
    模拟人脑：重要的事记得久，琐事会淡忘
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance INTEGER DEFAULT 5,
                recall_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                last_recalled REAL,
                embedding TEXT,
                expires_at REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(user_id, created_at)")
        conn.commit()
        conn.close()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def score(self, memory: dict, query_sim: float = 0.5) -> float:
        """计算记忆得分（重要性×衰减×相关性×强化）"""
        importance = memory.get("importance", 5)
        created_at = memory.get("created_at", time.time())
        recall_count = memory.get("recall_count", 0)

        age_days = (time.time() - created_at) / 86400

        # 艾宾浩斯遗忘曲线
        half_life = importance * 5  # 重要性越高，半衰期越长
        decay = math.exp(-age_days / half_life) if half_life > 0 else 0.1

        # 被回忆过会强化（间隔重复效应）
        reinforce = math.log(recall_count + 1) * 0.15

        # 过期检查
        expires_at = memory.get("expires_at")
        if expires_at and time.time() > expires_at:
            return 0

        return query_sim * 0.4 + importance / 10 * 0.3 + decay * 0.2 + reinforce * 0.1

    def store(self, user_id: str, content: str, memory_type: str,
              importance: int = 5, expires_at: float = None) -> int:
        """存储记忆"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO memories (user_id, content, memory_type, importance,
                   recall_count, created_at, last_recalled, expires_at)
                   VALUES (?, ?, ?, ?, 0, ?, NULL, ?)""",
                (user_id, content, memory_type, importance, time.time(), expires_at)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def recall(self, user_id: str, query: str = "", top_k: int = 5) -> List[dict]:
        """召回相关记忆（带评分排序）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT id, content, memory_type, importance, recall_count,
                   created_at, last_recalled, expires_at
                   FROM memories WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
                   ORDER BY created_at DESC LIMIT 50""",
                (user_id, time.time())
            ).fetchall()

            if not rows:
                return []

            memories = []
            for row in rows:
                mem = {
                    "id": row[0],
                    "content": row[1],
                    "memory_type": row[2],
                    "importance": row[3],
                    "recall_count": row[4],
                    "created_at": row[5],
                    "last_recalled": row[6],
                    "expires_at": row[7],
                }
                # 简单相关性（包含查询词）
                sim = 0.3
                if query and query in mem["content"]:
                    sim = 0.9
                elif query:
                    for word in query:
                        if word in mem["content"]:
                            sim = 0.5
                            break

                mem["score"] = self.score(mem, sim)
                memories.append(mem)

            # 按得分排序
            memories.sort(key=lambda m: m["score"], reverse=True)
            top = memories[:top_k]

            # 强化被回忆的记忆
            for m in top:
                self._reinforce(m["id"])

            return top
        finally:
            conn.close()

    def _reinforce(self, memory_id: int):
        """强化记忆（更新回忆次数）"""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE memories SET recall_count = recall_count + 1,
                   last_recalled = ? WHERE id = ?""",
                (time.time(), memory_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_profile(self, user_id: str) -> dict:
        """获取用户画像（基于记忆）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT content, memory_type, importance FROM memories
                   WHERE user_id = ? ORDER BY importance DESC, created_at DESC LIMIT 20""",
                (user_id,)
            ).fetchall()

            profile = {
                "facts": [],
                "preferences": [],
                "events": [],
                "emotions": [],
                "promises": []
            }

            for content, mtype, importance in rows:
                if mtype in profile:
                    profile[mtype].append(content)

            return profile
        finally:
            conn.close()

    def cleanup_expired(self):
        """清理过期记忆"""
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
                (time.time(),)
            )
            conn.commit()
        finally:
            conn.close()

    def get_stats(self, user_id: str) -> dict:
        """获取记忆统计"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT COUNT(*), AVG(importance), AVG(recall_count)
                   FROM memories WHERE user_id = ?""",
                (user_id,)
            ).fetchone()
            return {
                "total_memories": row[0] or 0,
                "avg_importance": round(row[1] or 0, 1),
                "avg_recall": round(row[2] or 0, 1)
            }
        finally:
            conn.close()


# 记忆抽取提示词
MEMORY_EXTRACT_PROMPT = """分析对话，提取需长期记住的信息，按类型输出JSON：
{
  "facts": [{"content": "用户是程序员", "importance": 7}],
  "preferences": [{"content": "喜欢喝美式", "importance": 6}],
  "events": [{"content": "下周一面试", "importance": 9, "expire_days": 7}],
  "emotions": [{"content": "最近工作压力大", "importance": 8}],
  "promises": [{"content": "答应周末陪用户看电影", "importance": 10}]
}
没有则返回 {}。只提取明确信息，不要推测。"""
