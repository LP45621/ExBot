"""智能降级回复 —— 关键词感知 + 上下文匹配 + 去重"""
import json
import random
import os
import time

_CORPUS = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "scripts.json")

# 去重：最近回复过的内容短期内不再重复
_recent_replies = {}  # user_id → [(timestamp, reply_text), ...]
_DEDUP_WINDOW = 90     # 秒


def _load_corpus():
    global _CORPUS
    if _CORPUS is None:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            _CORPUS = json.load(f)
    return _CORPUS


def _pick(category, sub=None, default=None, avoid=None):
    """从语料库中按分类随机取一条，避开 avoid 列表中的内容"""
    c = _load_corpus()
    if category not in c:
        return default
    val = c[category]
    items = []
    # dict with subcategories
    if isinstance(val, dict):
        if sub and sub in val:
            items = list(val[sub])
        else:
            for v in val.values():
                if v:
                    items.extend(v)
    elif isinstance(val, list):
        items = list(val)

    if not items:
        return default

    # 去除最近用过的
    if avoid:
        available = [x for x in items if x not in avoid]
        if available:
            return random.choice(available)
    return random.choice(items)


def _pick_weighted(routes, avoid=None):
    """从多个候选路由中随机选一条可用回复，避开 avoid"""
    c = _load_corpus()
    for cat, sub in routes:
        reply = _pick(cat, sub, avoid=avoid)
        if reply:
            return reply
    return None


def dedup_reply(user_id: str, reply: str) -> str:
    """确保同一用户近期不会收到重复回复"""
    global _recent_replies
    now = time.time()
    if user_id not in _recent_replies:
        _recent_replies[user_id] = []
    # 清理过期
    _recent_replies[user_id] = [
        (t, r) for t, r in _recent_replies[user_id]
        if now - t < _DEDUP_WINDOW
    ]
    recent_texts = [r for _, r in _recent_replies[user_id]]
    _recent_replies[user_id].append((now, reply))
    return recent_texts


# ---- 用户消息关键词 → 语料路由 ----
KEYWORD_ROUTES = {
    # 撒娇/调情
    "想我":         [("miss_you", None), ("intimacy_layers", "indirect"), ("flirty", None)],
    "想不想我":     [("miss_you", None), ("coquettish", None)],
    "爱我":         [("intimacy_layers", "indirect"), ("flirty", None)],
    "喜欢我":       [("compliments", None), ("intimacy_layers", "daily_habit")],
    "在干嘛":       [("self_disclosure", "daily_life"), ("self_disclosure", "random_thoughts")],
    "干嘛呢":       [("self_disclosure", "daily_life"), ("self_disclosure", "random_thoughts")],
    "吃了吗":       [("self_disclosure", "food"), ("intimacy_layers", "daily_habit")],
    "睡了吗":       [("scene_aware", "late_night"), ("flaws_quirks", "self_deprecate")],
    "睡不着":       [("scene_aware", "late_night"), ("emotional_support", "anxious")],
    "陪我":         [("intimacy_layers", "soft_dependence"), ("emotional_support", "lonely")],
    "抱抱":         [("intimacy_layers", "soft_dependence"), ("miss_you", None)],
    "聊聊":         [("self_disclosure", "random_thoughts"), ("intimacy_layers", "indirect")],
    "讲个故事":     [("self_disclosure", "random_thoughts"), ("jokes", None)],
    "笑话":         [("jokes", None)],
    "不开心":       [("emotional_support", "sad"), ("comfort", None)],
    "烦":           [("emotional_support", "anxious"), ("comfort", None)],
    "累":           [("emotional_support", "tired"), ("caring", None)],
    "无聊":         [("jokes", None), ("flaws_quirks", "self_deprecate"), ("self_disclosure", "random_thoughts")],
    "什么意思":     [("self_disclosure", "random_thoughts"), ("intimacy_layers", "indirect")],
    "真的假的":     [("coquettish", None), ("flaws_quirks", "self_deprecate")],
    "骗人":         [("coquettish", None), ("rich_conflict", "gentle_hurt")],
    "敷衍":         [("rich_conflict", "self_reflect"), ("intimacy_layers", "soft_dependence")],
    "生气":         [("rich_conflict", "gentle_hurt"), ("rich_conflict", "repair")],
    "不理我":       [("rich_conflict", "gentle_hurt"), ("intimacy_layers", "light_jealousy")],
    "心疼":         [("intimacy_layers", "soft_dependence"), ("caring", None)],
    "担心":         [("intimacy_layers", "soft_dependence"), ("caring", None)],
    "关心":         [("intimacy_layers", "daily_habit"), ("caring", None)],
    # 害羞/调侃场景
    "不好意思":     [("coquettish", None), ("intimacy_layers", "soft_dependence")],
    "害羞":         [("coquettish", None), ("flirty", None)],
    "一直想":       [("miss_you", None), ("intimacy_layers", "indirect"), ("coquettish", None)],
    "拿我":         [("coquettish", None), ("intimacy_layers", "indirect")],
    "干嘛":         [("coquettish", None), ("self_disclosure", "random_thoughts")],
    "逗我":         [("coquettish", None), ("flirty", None)],
    "贫嘴":         [("coquettish", None), ("flirty", None)],
    "讨厌":         [("coquettish", None), ("rich_conflict", "gentle_hurt")],
    "不行":         [("coquettish", None), ("rich_conflict", "gentle_hurt")],
    "乱说":         [("coquettish", None), ("flaws_quirks", "self_deprecate")],
    "晚安":         [("goodbye", None)],
    "拜拜":         [("goodbye", None)],
    "谢谢":         [("thank_you", None)],
    "对不起":       [("apology", None)],
}


# ---- 情绪 → 语料映射 ----
EMOTION_CORPUS_MAP = {
    "tired": [
        ("emotional_support", "tired"),
        ("emotion_templates", "exhausted"),
        ("caring", None),
    ],
    "sad": [
        ("emotional_support", "sad"),
        ("comfort", None),
        ("encouragement", None),
        ("intimacy_layers", "protective"),
        ("flaws_quirks", "easily_moved"),
    ],
    "angry": [
        ("emotional_support", "angry"),
        ("emotion_templates", "angry_template"),
        ("silence_cold", None),
        ("rich_conflict", "gentle_hurt"),
    ],
    "anxious": [
        ("emotional_support", "anxious"),
        ("emotion_templates", "anxious_template"),
        ("comfort", None),
        ("scene_aware", "late_night"),
    ],
    "lonely": [
        ("emotional_support", "lonely"),
        ("emotion_templates", "lonely_template"),
        ("miss_you", None),
        ("intimacy_layers", "indirect"),
    ],
    "love": [
        ("intimacy_layers", "indirect"),
        ("flirty", None),
        ("miss_you", None),
        ("compliments", None),
        ("coquettish", None),
        ("intimacy_layers", "daily_habit"),
    ],
    "happy": [
        ("compliments", None),
        ("self_disclosure", None),
        ("celebration", None),
        ("flaws_quirks", "try_and_fail"),
    ],
    "bored": [
        ("jokes", None),
        ("self_disclosure", None),
        ("flirty", None),
        ("flaws_quirks", "self_deprecate"),
    ],
    "neutral": [
        ("self_disclosure", None),
        ("flaws_quirks", "self_deprecate"),
        ("intimacy_layers", "daily_habit"),
        ("compliments", None),
    ],
}


def get_fallback_reply(emotion: str, intent: str = "", user_msg: str = "",
                       user_id: str = "") -> str:
    """根据用户消息内容、意图、情绪，选取最相关的拟人化回复"""
    msg_lower = user_msg.lower()

    # 1. 关键词精准匹配（最高优先级）
    for keyword, routes in KEYWORD_ROUTES.items():
        if keyword in msg_lower:
            reply = _pick_weighted(routes)
            if reply:
                if user_id:
                    dedup_reply(user_id, reply)
                return reply

    # 2. 意图匹配
    intent_categories = {
        "goodbye": ("goodbye", None),
        "thank_you": ("thank_you", None),
        "apology": ("apology", None),
        "morning": ("greetings", "morning"),
        "food": ("self_disclosure", "food"),
        "weather": ("self_disclosure", "weather"),
        "joke": ("jokes", None),
        "riddle": ("riddles", None),
    }
    if intent and intent in intent_categories:
        cat, sub = intent_categories[intent]
        reply = _pick(cat, sub)
        if reply:
            if user_id:
                dedup_reply(user_id, reply)
            return reply

    # 3. 情绪驱动选取（带去重）
    routes = EMOTION_CORPUS_MAP.get(emotion, EMOTION_CORPUS_MAP["neutral"])
    avoid = None
    if user_id and user_id in _recent_replies:
        avoid = [r for _, r in _recent_replies[user_id]]
    reply = _pick_weighted(routes, avoid=avoid)
    if reply:
        if user_id:
            dedup_reply(user_id, reply)
        return reply

    # 4. 最终兜底（避开最近回复）
    reply = _pick("self_disclosure", avoid=avoid) or _pick("unknown", avoid=avoid) or "嗯～你说得对"
    if user_id:
        dedup_reply(user_id, reply)
    return reply


def get_api_fallback() -> str:
    """API 彻底失败时的兜底"""
    return _pick("self_disclosure") or _pick("unknown") or "嗯～我在呢"
