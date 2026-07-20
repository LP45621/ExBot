"""人类化记忆系统 - 带遗忘曲线和强化机制"""
import math
import time
import json
import sqlite3
import os
from typing import List, Dict, Optional


class HumanLikeMemory:
    """
    人类化记忆系统 —— 模拟人脑记忆的四个核心特性

    1. 重要性加权 (importance ∈ [1,10]):
       重要的事记得久，琐事会淡忘

    2. Ebbinghaus 遗忘曲线 + 近期热度:
       score = query_sim×0.35 + (importance/10)×0.2 + decay×0.15
             + recency×0.15 + emotion_match×0.1 + reinforce×0.05
       decay = exp(-age_days / half_life)
       recency = exp(-age_hours / 72)
       half_life = importance × 5  (高重要性 → 长半衰期)

    3. 间隔重复效应 (Spaced Repetition):
       reinforce = ln(recall_count + 1) × 0.15
       每次被回忆都会强化记忆权重

    4. 情绪标签:
       每条记忆可带 emotion_tag, 当前情绪匹配时优先召回

    5. 话题相关性匹配:
       sim = 0.9 (精确匹配) / 0.5 (分词匹配) / 0.3 (无关)
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
                expires_at REAL,
                emotion_tag TEXT DEFAULT ''
            )
        """)
        self._ensure_column(conn, "memories", "emotion_tag", "TEXT DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(user_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_emotion ON memories(user_id, emotion_tag)")
        conn.commit()
        conn.close()

    def _ensure_column(self, conn, table: str, column: str, definition: str):
        """兼容旧库：缺列时自动补上。"""
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def score(self, memory: dict, query_sim: float = 0.5,
              current_emotion: str = "") -> float:
        """计算记忆得分（相关性×重要性×衰减×近期×情绪×强化）"""
        importance = memory.get("importance", 5)
        created_at = memory.get("created_at", time.time())
        recall_count = memory.get("recall_count", 0)
        emotion_tag = memory.get("emotion_tag", "")

        age_days = (time.time() - created_at) / 86400
        age_hours = max(0, (time.time() - created_at) / 3600)

        # 艾宾浩斯遗忘曲线
        half_life = importance * 5  # 重要性越高，半衰期越长
        decay = math.exp(-age_days / half_life) if half_life > 0 else 0.1

        # 近期热度：最近3天内的记忆会更容易浮上来
        recency = math.exp(-age_hours / 72)

        # 情绪匹配：同情绪场景更容易被想起，负面情绪互相兼容
        emotion_match = self._emotion_match(emotion_tag, current_emotion)

        # 被回忆过会强化（间隔重复效应）
        reinforce = math.log(recall_count + 1) * 0.15

        # 过期检查
        expires_at = memory.get("expires_at")
        if expires_at and time.time() > expires_at:
            return 0

        return (
            query_sim * 0.35
            + importance / 10 * 0.2
            + decay * 0.15
            + recency * 0.15
            + emotion_match * 0.1
            + reinforce * 0.05
        )

    def _emotion_match(self, memory_emotion: str, current_emotion: str) -> float:
        if not memory_emotion or not current_emotion:
            return 0.2
        if memory_emotion == current_emotion:
            return 1.0
        negative = {"sad", "angry", "tired", "anxious", "lonely"}
        positive = {"happy", "love"}
        if memory_emotion in negative and current_emotion in negative:
            return 0.7
        if memory_emotion in positive and current_emotion in positive:
            return 0.6
        return 0.0

    def store(self, user_id: str, content: str, memory_type: str,
              importance: int = 5, expires_at: float = None,
              emotion_tag: str = "") -> int:
        """存储记忆"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO memories (user_id, content, memory_type, importance,
                   recall_count, created_at, last_recalled, expires_at, emotion_tag)
                   VALUES (?, ?, ?, ?, 0, ?, NULL, ?, ?)""",
                (user_id, content, memory_type, importance, time.time(), expires_at, emotion_tag)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def recall(self, user_id: str, query: str = "", top_k: int = 5,
               current_emotion: str = "") -> List[dict]:
        """召回相关记忆（带评分排序）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT id, content, memory_type, importance, recall_count,
                   created_at, last_recalled, expires_at, emotion_tag
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
                    "emotion_tag": row[8] or "",
                }
                # 简单相关性（包含查询词）
                sim = self._query_similarity(mem["content"], query)

                mem["score"] = self.score(mem, sim, current_emotion)
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

    def _query_similarity(self, content: str, query: str) -> float:
        if not query:
            return 0.3
        if query in content or content in query:
            return 0.9

        query_tokens = self._tokens(query)
        content_tokens = self._tokens(content)
        if not query_tokens or not content_tokens:
            return 0.3

        overlap = query_tokens & content_tokens
        if not overlap:
            return 0.3
        ratio = len(overlap) / max(1, min(len(query_tokens), len(content_tokens)))
        return min(0.8, 0.45 + ratio * 0.35)

    def _tokens(self, text: str) -> set:
        words = set()
        buff = []
        for ch in text.lower():
            if ch.isalnum():
                buff.append(ch)
            else:
                if buff:
                    words.add("".join(buff))
                    buff = []
        if buff:
            words.add("".join(buff))

        # 中文短文本没有空格，补充2字滑窗提升相关性
        compact = "".join(ch for ch in text if not ch.isspace())
        if len(compact) >= 2:
            words.update(compact[i:i + 2] for i in range(len(compact) - 1))
        return words

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
                """SELECT content, memory_type, importance, emotion_tag FROM memories
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

            for content, mtype, importance, emotion_tag in rows:
                if mtype in profile:
                    profile[mtype].append({
                        "content": content,
                        "emotion_tag": emotion_tag or "",
                        "importance": importance
                    })

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
  "facts": [{"content": "用户是程序员", "importance": 7, "emotion_tag": "neutral"}],
  "preferences": [{"content": "喜欢喝美式", "importance": 6, "emotion_tag": "happy"}],
  "events": [{"content": "下周一面试", "importance": 9, "expire_days": 7, "emotion_tag": "anxious"}],
  "emotions": [{"content": "最近工作压力大", "importance": 8, "emotion_tag": "tired"}],
  "promises": [{"content": "答应周末陪用户看电影", "importance": 10, "emotion_tag": "love"}]
}
没有则返回 {}。只提取明确信息，不要推测。"""
