"""AI 模块 - 深度优化版"""
import sys
import os
import httpx
import random
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "less_tokens_pkg"))

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL,
    MAX_HISTORY, SUMMARY_THRESHOLD
)
from memory import (
    save_message, get_history, get_user_summary,
    save_user_summary, get_message_count
)
from token_optimizer import compress_history
from auto_memory import load_user_memory, update_memory_from_conversation, get_memory_context
from engine import (
    detect_emotion, detect_intent, get_simple_reply, should_use_llm,
    route_model, build_messages, _mood_engine, _emotion_detector,
    extract_memory_from_conversation, get_memory_system
)

USE_MOCK = not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.startswith("your_")


async def call_deepseek(messages: list, request_id: str = "") -> str:
    """调用 MiMo API（带超时、重试、指数退避）"""
    if USE_MOCK:
        last_msg = messages[-1]["content"] if messages else ""
        from engine import get_script_db
        get = get_script_db()
        if get:
            emotion = detect_emotion(last_msg)
            intent = detect_intent(last_msg)
            if intent:
                reply = get(intent if intent != "hello" else "hello")
                if reply:
                    return reply
            if emotion and emotion != "neutral":
                reply = get("emotional_responses", emotion)
                if reply:
                    return reply
        return random.choice([
            "嗯嗯～你说的对", "然后呢～", "我明白了～",
            "真的吗～", "哈哈～", "你说得有道理呢"
        ])

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 256
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"]
                return "我好像有点累了～休息一下"
        except httpx.TimeoutException:
            if attempt < 2:
                await asyncio.sleep(1 * (attempt + 1))
                continue
            return random.choice(["让我缓一下，刚刚走神啦~", "网有点卡，再说一遍嘛？"])
        except Exception:
            if attempt < 2:
                await asyncio.sleep(1 * (attempt + 1))
                continue
            return random.choice(["网络不太好呢～稍后再聊", "哎呀断线了，你再说一次"])

    return "我好像有点累了～休息一下"


async def auto_summarize(user_id: str):
    """自动摘要对话历史"""
    try:
        history = get_history(user_id, limit=50)
        if len(history) < SUMMARY_THRESHOLD:
            return
        summary_prompt = [
            {"role": "system", "content": "请用3-5句话总结以下对话的关键信息，包括用户的名字、喜好、情绪状态、重要事件、承诺。直接输出总结。"},
            {"role": "user", "content": "\n".join(f"{r}: {c}" for r, c in history)}
        ]
        summary = await call_deepseek(summary_prompt)
        save_user_summary(user_id, summary)
    except Exception:
        pass


async def get_ai_reply(user_id: str, user_message: str, request_id: str = "") -> str:
    """获取 AI 回复（主入口）"""
    if not user_message or not user_message.strip():
        return "你怎么不说话呀～"

    user_message = user_message.strip()[:500]

    # 保存消息
    save_message(user_id, "user", user_message)

    # 检测情绪
    emotion = detect_emotion(user_message)
    intent = detect_intent(user_message)

    # 更新AI心情
    _mood_engine.update(emotion)

    # 判断是否需要调用LLM
    if not should_use_llm(user_message, emotion):
        simple_reply = get_simple_reply(intent)
        if simple_reply:
            save_message(user_id, "assistant", simple_reply)
            update_memory_from_conversation(user_id, user_message, simple_reply)
            extract_memory_from_conversation(user_id, user_message, simple_reply)
            return simple_reply

    # 后台摘要
    msg_count = get_message_count(user_id)
    if msg_count > 0 and msg_count % SUMMARY_THRESHOLD == 0:
        asyncio.create_task(auto_summarize(user_id))

    # 构建消息（带压缩）
    history = get_history(user_id, limit=MAX_HISTORY)
    user_memory = load_user_memory(user_id)
    user_memory["user_id"] = user_id
    messages = build_messages(user_message, history, user_memory, emotion)

    # 调用 API
    reply = await call_deepseek(messages, request_id)

    # 保存回复
    save_message(user_id, "assistant", reply)
    update_memory_from_conversation(user_id, user_message, reply)
    extract_memory_from_conversation(user_id, user_message, reply)

    return reply
