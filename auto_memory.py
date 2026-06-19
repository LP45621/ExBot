"""自动记忆模块 - 记住用户所有关键信息"""
import os
import json
import time
import sqlite3
from typing import Optional

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memories")


def _ensure_dir():
    os.makedirs(MEMORY_DIR, exist_ok=True)


def _get_memory_path(user_id: str) -> str:
    _ensure_dir()
    safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
    return os.path.join(MEMORY_DIR, f"{safe_id}.json")


def load_user_memory(user_id: str) -> dict:
    """加载用户记忆"""
    path = _get_memory_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "user_id": user_id,
        "name": "",
        "nickname": "",
        "preferences": [],
        "important_events": [],
        "emotional_patterns": [],
        "topics_discussed": [],
        "first_met": int(time.time()),
        "last_chat": int(time.time()),
        "total_messages": 0,
        "personality_notes": ""
    }


def save_user_memory(user_id: str, memory: dict):
    """保存用户记忆"""
    path = _get_memory_path(user_id)
    memory["last_chat"] = int(time.time())
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def update_memory_from_conversation(user_id: str, user_msg: str, ai_reply: str):
    """从对话中提取信息更新记忆"""
    memory = load_user_memory(user_id)
    memory["total_messages"] = memory.get("total_messages", 0) + 1
    memory["last_chat"] = int(time.time())

    msg_lower = user_msg.lower()

    # 提取名字
    name_patterns = ["我叫", "我是", "我的名字", "叫我", "名字是"]
    for pattern in name_patterns:
        if pattern in msg_lower:
            start = msg_lower.find(pattern) + len(pattern)
            end = min(start + 10, len(user_msg))
            name = user_msg[start:end].strip().split()[0] if start < len(user_msg) else ""
            if name and len(name) <= 10:
                memory["name"] = name
                break

    # 提取昵称
    nick_patterns = ["叫我", "你可以叫我", "昵称", "小名"]
    for pattern in nick_patterns:
        if pattern in msg_lower:
            start = msg_lower.find(pattern) + len(pattern)
            end = min(start + 10, len(user_msg))
            nick = user_msg[start:end].strip().split()[0] if start < len(user_msg) else ""
            if nick and len(nick) <= 10:
                memory["nickname"] = nick
                break

    # 提取喜好
    like_patterns = ["喜欢", "爱", "最爱", "最喜欢"]
    for pattern in like_patterns:
        if pattern in msg_lower:
            start = msg_lower.find(pattern) + len(pattern)
            end = min(start + 20, len(user_msg))
            preference = user_msg[start:end].strip()
            if preference and len(preference) <= 20:
                if preference not in memory["preferences"]:
                    memory["preferences"].append(preference)
                break

    # 提取重要事件
    event_patterns = ["今天", "昨天", "刚才", "之前", "上次"]
    for pattern in event_patterns:
        if pattern in msg_lower:
            event = user_msg[:50] if len(user_msg) > 50 else user_msg
            if event not in memory["important_events"][-10:]:
                memory["important_events"].append(event)
                if len(memory["important_events"]) > 20:
                    memory["important_events"] = memory["important_events"][-20:]
            break

    # 提取情绪模式
    emotion_words = {
        "开心": "happy", "高兴": "happy", "难过": "sad", "伤心": "sad",
        "生气": "angry", "累": "tired", "困": "tired", "无聊": "bored",
        "喜欢": "love", "想你": "love"
    }
    for word, emotion in emotion_words.items():
        if word in msg_lower:
            pattern = f"{emotion}:{int(time.time())}"
            memory["emotional_patterns"].append(pattern)
            if len(memory["emotional_patterns"]) > 50:
                memory["emotional_patterns"] = memory["emotional_patterns"][-50:]
            break

    # 提取讨论话题
    topic_keywords = ["工作", "学习", "游戏", "电影", "音乐", "美食", "旅行", "运动", "宠物"]
    for topic in topic_keywords:
        if topic in msg_lower:
            if topic not in memory["topics_discussed"]:
                memory["topics_discussed"].append(topic)
            break

    save_user_memory(user_id, memory)
    return memory


def get_memory_context(user_id: str) -> str:
    """获取记忆上下文（用于 AI prompt）"""
    memory = load_user_memory(user_id)
    context_parts = []

    if memory.get("name"):
        context_parts.append(f"用户姓名：{memory['name']}")
    if memory.get("nickname"):
        context_parts.append(f"昵称：{memory['nickname']}")
    if memory.get("preferences"):
        context_parts.append(f"喜好：{', '.join(memory['preferences'][:5])}")
    if memory.get("topics_discussed"):
        context_parts.append(f"讨论过的话题：{', '.join(memory['topics_discussed'])}")
    if memory.get("important_events"):
        recent_events = memory["important_events"][-3:]
        context_parts.append(f"最近提到的事：{'; '.join(recent_events)}")
    if memory.get("personality_notes"):
        context_parts.append(f"性格特点：{memory['personality_notes']}")

    days_known = (time.time() - memory.get("first_met", time.time())) / 86400
    if days_known > 1:
        context_parts.append(f"认识天数：{int(days_known)}天")

    return "；".join(context_parts) if context_parts else ""


def get_memory_stats(user_id: str) -> dict:
    """获取记忆统计"""
    memory = load_user_memory(user_id)
    return {
        "name": memory.get("name", ""),
        "preferences_count": len(memory.get("preferences", [])),
        "events_count": len(memory.get("important_events", [])),
        "topics_count": len(memory.get("topics_discussed", [])),
        "total_messages": memory.get("total_messages", 0),
        "days_known": int((time.time() - memory.get("first_met", time.time())) / 86400)
    }
