"""核心引擎 - 深度优化版"""
import sys
import os
import time
import random
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "less_tokens_pkg"))

from config import (
    SIMPLE_REPLIES, EMOTION_KEYWORDS, INTENT_KEYWORDS,
    MODEL_ROUTING, MEMORY_DB_PATH
)
from token_optimizer import compress_history
from mood import MoodEngine, EmotionDetector
from human_memory import HumanLikeMemory

# 全局实例
_mood_engine = MoodEngine()
_emotion_detector = EmotionDetector()
_memory_system = None
_script_db = None


def get_memory_system():
    global _memory_system
    if _memory_system is None:
        _memory_system = HumanLikeMemory(MEMORY_DB_PATH)
    return _memory_system




def detect_emotion(text: str) -> str:
    """检测用户情绪"""
    return _emotion_detector.detect(text)


def detect_intent(text: str) -> str:
    """检测用户意图"""
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return intent
    return None


# intent 到 SIMPLE_REPLIES 键的映射（修复键名不匹配导致模板回复全部失效的 bug）
INTENT_TO_TEMPLATE_KEY = {
    "morning": "早",
    "goodbye": "晚安",
    "hello": "在吗",
    "thank_you": "谢谢",
}


def get_simple_reply(intent: str, raw_msg: str = "") -> str:
    """获取简单回复（不调用LLM）"""
    # 优先：intent 直接匹配 SIMPLE_REPLIES
    if intent in SIMPLE_REPLIES:
        return random.choice(SIMPLE_REPLIES[intent])

    # 其次：通过映射表转换 intent → template key
    template_key = INTENT_TO_TEMPLATE_KEY.get(intent)
    if template_key and template_key in SIMPLE_REPLIES:
        return random.choice(SIMPLE_REPLIES[template_key])

    # 兜底：用原始消息直接匹配 SIMPLE_REPLIES 的键
    for keyword, replies in SIMPLE_REPLIES.items():
        if keyword in raw_msg:
            return random.choice(replies)

    return None


def should_use_llm(user_message: str, emotion: str) -> bool:
    """判断是否需要调用LLM"""
    stripped = user_message.strip().rstrip("？?。!~…")
    for keyword in MODEL_ROUTING["template"]:
        if stripped == keyword:
            return False
    if len(user_message) < 6 and emotion == "neutral":
        return False
    return True


def route_model(user_message: str, emotion: str, context_len: int) -> str:
    """模型路由"""
    stripped = user_message.strip().rstrip("？?。!~…")
    for keyword in MODEL_ROUTING["template"]:
        if stripped == keyword:
            return "template"
    for keyword in MODEL_ROUTING["cheap"]:
        if keyword in user_message:
            return "cheap"
    if emotion in MODEL_ROUTING["premium_emotions"]:
        return "premium"
    for keyword in MODEL_ROUTING["premium_keywords"]:
        if keyword in user_message:
            return "premium"
    return "cheap"


def build_persona(user_memory: dict, emotion: str, user_msg: str = "",
                  user_id: str = "") -> str:
    """构建动态人设 —— 四层提示词架构 L1+L2+L3"""
    now = datetime.now()
    hour = now.hour

    if 5 <= hour < 9:       time_greeting = "早上好"
    elif 9 <= hour < 12:    time_greeting = "上午好"
    elif 12 <= hour < 14:   time_greeting = "中午好"
    elif 14 <= hour < 18:   time_greeting = "下午好"
    elif 18 <= hour < 22:   time_greeting = "晚上好"
    else:                   time_greeting = "夜深了"

    nickname = user_memory.get("nickname") or user_memory.get("name") or "亲爱的"
    preferences = ", ".join(user_memory.get("preferences", [])[:3]) or "暂无"
    first_met = user_memory.get("first_met", time.time())
    days_known = max(1, int((time.time() - first_met) / 86400))

    # L3 记忆层：按当前话题匹配
    memories = get_memory_system().recall(user_memory.get("user_id", ""), user_msg, top_k=3)
    key_memories = "；".join([m["content"] for m in memories]) if memories else "暂无"

    ai_mood = _mood_engine.to_prompt()

    emotion_map = {
        "happy": "开心", "sad": "难过", "angry": "生气",
        "tired": "疲惫", "love": "想你", "bored": "无聊", "neutral": "平静"
    }
    user_emotion_desc = emotion_map.get(emotion, "平静")

    # L1 灵魂层 + L2 性格层 + L3 记忆层
    from soul_layer import SOUL_LAYER, build_personality_layer, get_rhythm_controller
    rhythm = get_rhythm_controller()
    rhythm_hint = rhythm.get_rhythm_hint(user_id, user_msg, emotion=emotion)

    # L2: 性格参数
    from ai import _user_persona
    persona_params = _user_persona.get(user_id, {})
    l2_personality = build_personality_layer(persona_params)

    return f"""{SOUL_LAYER}

{l2_personality if l2_personality else "【性格层】自然状态"}

【当前状态】
现在{time_greeting}，{now.strftime('%H:%M')}
对方：{nickname}，感觉{user_emotion_desc}
你：{ai_mood}
认识{days_known}天
喜好：{preferences}
记忆：{key_memories}

{rhythm_hint if rhythm_hint else ""}"""


def build_messages(user_message: str, history: list, user_memory: dict, emotion: str,
                   user_id: str = "") -> list:
    """构建API消息列表"""
    messages = []

    persona = build_persona(user_memory, emotion, user_message, user_id=user_id)
    messages.append({"role": "system", "content": persona})

    if history:
        compressed = compress_history(history)
        for role, content in compressed:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    return messages


def split_reply(text: str) -> list:
    """拆分回复为多条消息"""
    if not text:
        return []

    sentences = re.split(r'(?<=[。！？~…])\s*', text.strip())
    result = []
    for s in sentences:
        s = s.strip()
        if s and len(s) > 1:
            result.append(s)

    return result if result else [text]


def extract_memory_from_conversation(user_id: str, user_msg: str, ai_reply: str):
    """从对话中提取记忆"""
    memory = get_memory_system()
    msg_lower = user_msg.lower()

    name_patterns = ["我叫", "我是", "我的名字", "叫我"]
    for pattern in name_patterns:
        if pattern in msg_lower:
            start = msg_lower.find(pattern) + len(pattern)
            end = min(start + 10, len(user_msg))
            name = user_msg[start:end].strip().split()[0] if start < len(user_msg) else ""
            if name and len(name) <= 10:
                memory.store(user_id, f"用户名字是{name}", "facts", importance=8)
                break

    like_patterns = ["喜欢", "爱", "最爱", "最喜欢"]
    for pattern in like_patterns:
        if pattern in msg_lower:
            start = msg_lower.find(pattern) + len(pattern)
            end = min(start + 20, len(user_msg))
            preference = user_msg[start:end].strip()
            if preference and len(preference) <= 20:
                memory.store(user_id, f"用户喜欢{preference}", "preferences", importance=6)
            break

    event_patterns = ["今天", "昨天", "刚才", "之前", "上次", "下周", "明天"]
    for pattern in event_patterns:
        if pattern in msg_lower:
            event = user_msg[:50] if len(user_msg) > 50 else user_msg
            memory.store(user_id, event, "events", importance=7)
            break

    promise_patterns = ["答应", "说好", "保证", "承诺"]
    for pattern in promise_patterns:
        if pattern in msg_lower:
            promise = user_msg[:50] if len(user_msg) > 50 else user_msg
            memory.store(user_id, promise, "promises", importance=10)
            break

    emotion_words = ["压力", "焦虑", "迷茫", "开心", "难过", "生气"]
    for word in emotion_words:
        if word in msg_lower:
            memory.store(user_id, f"用户最近{word}", "emotions", importance=7)
            break
