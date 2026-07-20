"""AI 模块 —— DeepSeek Flash 优化版"""
import httpx
import random
import asyncio
import logging

logger = logging.getLogger("wechat")

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
    route_model, build_messages,
    extract_memory_from_conversation, get_memory_system,
    _mood_engine
)
from reply_fallback import get_fallback_reply, get_api_fallback

# Token 优化配置
MAX_TOKENS_REPLY = 50      # 回复最大 token（Flash 模型响应快，可压缩）
MAX_TOKENS_IMAGE = 40      # 图片回复最大 token
MAX_TOKENS_SUMMARY = 80    # 摘要最大 token


def _first_sentence(text: str, allow_two: bool = False) -> str:
    """尽量保持简短。allow_two=True 时允许关键词追问"""
    if not text:
        return text
    first_cut = len(text)
    for sep in ['。', '！', '？', '!', '?']:
        idx = text.find(sep)
        if 0 < idx < first_cut:
            first_cut = idx
    if first_cut < len(text):
        text = text[:first_cut]
    return text[:40] if len(text) > 40 else text


# 性格指令关键词
PERSONA_COMMANDS = {
    "更温柔": ("温柔", 0.2), "更暖": ("温柔", 0.2),
    "活泼": ("活泼", 0.2), "调皮": ("活泼", 0.2), "有趣": ("活泼", 0.15),
    "傲娇": ("傲娇", 0.25), "高冷": ("傲娇", 0.2), "毒舌": ("傲娇", 0.3),
    "粘人": ("主动", 0.2), "主动": ("主动", 0.15),
    "话多": ("话量", 0.2), "话少": ("话量", -0.2), "少说": ("话量", -0.2),
    "撒娇": ("撒娇", 0.2),
    "怼我": ("吐槽", 0.2), "毒舌": ("吐槽", 0.3),
    "成熟": ("成熟", 0.2), "姐姐": ("成熟", 0.2),
    "正常": ("重置", 0), "恢复": ("重置", 0), "默认": ("重置", 0),
}

_user_persona = {}


def get_user_persona_prompt(user_id: str) -> str:
    """获取用户当前的性格参数→自然语言提示"""
    params = _user_persona.get(user_id, {})
    if not params:
        return ""
    parts = []
    desc = {
        "温柔": ("更温柔一点", "可以偶尔怼人"),
        "活泼": ("活泼调皮一点", "正经一点"),
        "傲娇": ("带点傲娇，口是心非", "直球一点"),
        "主动": ("主动找话题、主动关心", "被动回应就好"),
        "话量": ("多说几句", "精简一点"),
        "撒娇": ("多撒娇", "少撒娇"),
        "吐槽": ("可以吐槽怼人", "温柔说话"),
        "成熟": ("成熟姐姐风", "可爱少女风"),
    }
    for k, v in params.items():
        if abs(v) < 0.1:
            continue
        d = desc.get(k, ("", ""))
        text = d[0] if v > 0 else d[1]
        parts.append(text)
    return "性格偏好：" + "，".join(parts) if parts else ""


def apply_persona_command(user_id: str, user_msg: str) -> str:
    """检测并应用用户性格指令"""
    msg_lower = user_msg.lower()
    for keyword, (dim, delta) in PERSONA_COMMANDS.items():
        if keyword in msg_lower:
            if user_id not in _user_persona:
                _user_persona[user_id] = {}
            if dim == "重置":
                _user_persona[user_id] = {}
                return "好，我变回自己啦"
            old = _user_persona[user_id].get(dim, 0)
            _user_persona[user_id][dim] = max(-1, min(1, old + delta))
            return f"知道啦～我会{keyword}一点的"
    return ""


USE_MOCK = not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.startswith("your_")


async def call_deepseek(messages: list, request_id: str = "",
                        max_tokens: int = MAX_TOKENS_REPLY) -> str:
    """调用 DeepSeek API（带超时、重试）"""
    if USE_MOCK:
        return get_api_fallback()

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": max_tokens,
        "top_p": 0.9
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content", "")
                    if content and content.strip():
                        # 记录 token 使用
                        usage = data.get("usage", {})
                        if usage:
                            logger.info(f"[{request_id}] Tokens: prompt={usage.get('prompt_tokens', '?')} completion={usage.get('completion_tokens', '?')}")
                        return content.strip()
                    logger.warning(f"[{request_id}] Empty content from API")
                return get_api_fallback()
        except httpx.TimeoutException:
            if attempt < 1:
                await asyncio.sleep(1)
                continue
            return _smart_fallback(messages)
        except Exception as e:
            if attempt < 1:
                await asyncio.sleep(1)
                continue
            logger.error(f"[{request_id}] API error: {e}")
            return _smart_fallback(messages)

    return _smart_fallback(messages)


def _smart_fallback(messages: list) -> str:
    """从语料库选场景化回复"""
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break
    emotion = detect_emotion(last_user_msg)
    intent = detect_intent(last_user_msg)
    return get_fallback_reply(emotion, intent, last_user_msg)


async def auto_summarize(user_id: str):
    """自动摘要对话历史"""
    try:
        history = get_history(user_id, limit=30)
        if len(history) < SUMMARY_THRESHOLD:
            return
        summary_prompt = [
            {"role": "system", "content": "用3句话总结对话要点：用户特征、情绪、重要事件。"},
            {"role": "user", "content": "\n".join(f"{r}: {c}" for r, c in history[-20:])}
        ]
        summary = await call_deepseek(summary_prompt, max_tokens=MAX_TOKENS_SUMMARY)
        save_user_summary(user_id, summary)
    except Exception:
        pass


# AI 不回复的概率配置
IGNORE_PROBABILITY = {
    "meaningless": 0.70,   # 无意义符号（?、。、…），70%概率不回复
    "very_short": 0.40,    # 1-2个字的消息，40%概率不回复
    "short": 0.20,         # 3-5个字的消息，20%概率不回复
    "bad_mood": 0.30,      # AI心情差时，30%概率不回复
    "sulking": 0.50,       # AI闹脾气时，50%概率不回复
    "excited": 0.05,       # AI兴奋时，5%概率不回复（几乎都会回）
}

# 无意义消息列表（直接忽略或高概率忽略）
MEANINGLESS_MESSAGES = {'?', '？', '。', '...', '。。。', '…', '..', '..', '??', '？？'}

def should_ignore_message(message: str, emotion: str) -> bool:
    """判断AI是否应该选择不回复（模拟真人有时不回消息）"""
    mood = _mood_engine
    msg = message.strip()
    
    # 无意义消息直接高概率忽略
    if msg in MEANINGLESS_MESSAGES or len(msg) <= 1:
        if random.random() < IGNORE_PROBABILITY["meaningless"]:
            logger.info(f"AI ignoring meaningless message: {msg}")
            return True
    
    # 闹脾气时有概率不回复
    if mood.is_sulking():
        if random.random() < IGNORE_PROBABILITY["sulking"]:
            logger.info(f"AI sulking, ignoring message: {msg[:20]}")
            return True
    
    # 兴奋时几乎都会回复
    if mood.is_excited():
        if random.random() < IGNORE_PROBABILITY["excited"]:
            return True
        return False
    
    # 心情差时有概率不回复
    if mood.mood < 0.3:
        if random.random() < IGNORE_PROBABILITY["bad_mood"]:
            logger.info(f"AI bad mood ({mood.mood:.2f}), ignoring: {msg[:20]}")
            return True
    
    # 根据消息长度决定是否回复
    msg_len = len(msg)
    if msg_len <= 2:
        if random.random() < IGNORE_PROBABILITY["very_short"]:
            logger.info(f"AI ignoring very short: {msg}")
            return True
    elif msg_len <= 5:
        if random.random() < IGNORE_PROBABILITY["short"]:
            logger.info(f"AI ignoring short: {msg}")
            return True
    
    return False


# 防重复回复机制
def _check_and_break_repetition(user_id: str, reply: str, history: list) -> str:
    """检查回复是否和最近的回复太相似，如果是则强制换一个"""
    if not reply or not history:
        return reply
    
    # 提取最近的 assistant 回复
    recent_replies = [content for role, content in history if role == "assistant"][-5:]
    
    if not recent_replies:
        return reply
    
    # 检查新回复是否和最近回复重复
    reply_short = reply[:20]  # 只比较前20个字符
    for recent in recent_replies:
        recent_short = recent[:20]
        # 如果前20个字符完全相同或高度相似
        if reply_short == recent_short or reply_short in recent_short or recent_short in reply_short:
            # 使用备用回复
            fallback_replies = [
                "嗯？你说啥",
                "怎么啦",
                "我在呢",
                "说吧",
                "嗯嗯",
                "怎么了",
                "我在听",
                "嗯 你说",
                "怎么了呀",
                "嗯？",
            ]
            new_reply = random.choice(fallback_replies)
            logger.info(f"[{user_id}] Repetitive reply detected, switching to: {new_reply}")
            return new_reply
    
    return reply


async def get_ai_reply(user_id: str, user_message: str, request_id: str = "",
                      deadline: float = 0.0, skip_save_user: bool = False) -> str:
    """获取 AI 回复（主入口）"""
    if not user_message or not user_message.strip():
        return "你怎么不说话呀～"

    user_message = user_message.strip()[:300]  # 限制输入长度

    # 检测性格指令
    persona_cmd_reply = apply_persona_command(user_id, user_message)
    if persona_cmd_reply:
        save_message(user_id, "assistant", persona_cmd_reply)
        return persona_cmd_reply

    # 保存消息
    if not skip_save_user:
        save_message(user_id, "user", user_message)

    # 检测情绪
    emotion = detect_emotion(user_message)
    intent = detect_intent(user_message)

    # 更新AI心情
    _mood_engine.update(emotion)

    # AI 选择不回复（模拟真人行为）
    if should_ignore_message(user_message, emotion):
        return ""  # 返回空串表示不回复

    # 判断是否需要调用LLM
    if not should_use_llm(user_message, emotion):
        simple_reply = get_simple_reply(intent, user_message)
        if simple_reply:
            save_message(user_id, "assistant", simple_reply)
            update_memory_from_conversation(user_id, user_message, simple_reply)
            extract_memory_from_conversation(user_id, user_message, simple_reply)
            return simple_reply

    # 后台摘要
    if not skip_save_user:
        msg_count = get_message_count(user_id)
        if msg_count > 0 and msg_count % SUMMARY_THRESHOLD == 0:
            asyncio.create_task(auto_summarize(user_id))

    # 构建消息（带压缩）
    history = get_history(user_id, limit=MAX_HISTORY)
    user_memory = load_user_memory(user_id)
    user_memory["user_id"] = user_id
    messages = build_messages(user_message, history, user_memory, emotion, user_id=user_id)

    # 调用 API
    if deadline > 0:
        reply = await asyncio.wait_for(
            call_deepseek(messages, request_id),
            timeout=deadline
        )
    else:
        reply = await call_deepseek(messages, request_id)

    # 防重复：检查是否和最近回复太相似
    reply = _check_and_break_repetition(user_id, reply, history)

    # 保存回复
    if not reply or not reply.strip():
        reply = get_fallback_reply(emotion, intent, user_message, user_id=user_id)
    save_message(user_id, "assistant", reply)
    update_memory_from_conversation(user_id, user_message, reply)
    extract_memory_from_conversation(user_id, user_message, reply)

    return reply


async def get_ai_image_reply(user_id: str, pic_url: str, text: str = "",
                             request_id: str = "") -> str:
    """处理图片消息"""
    history = get_history(user_id, limit=3)

    prompt = "朋友发了图片。用1句话自然回应，可以猜内容或调侃。"

    messages = [{"role": "system", "content": prompt}]
    for role, content in history[-2:]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": "[图片]"})

    try:
        reply = await call_deepseek(messages, request_id, max_tokens=MAX_TOKENS_IMAGE)
        save_message(user_id, "assistant", reply)
        return reply
    except Exception as e:
        logger.error(f"[{request_id}] Image reply error: {e}")

    return random.choice([
        "哈哈哈这是啥",
        "笑死，你哪来的图",
        "这图好搞笑",
    ])
