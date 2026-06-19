"""智能降级回复 —— 从 scripts.json 语料库按场景选取人性化回复"""
import json
import random
import os

_CORPUS = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "scripts.json")


def _load_corpus():
    global _CORPUS
    if _CORPUS is None:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            _CORPUS = json.load(f)
    return _CORPUS


def _pick(category, sub=None, default=None):
    """从语料库中按分类随机取一条，支持子分类随机选取"""
    c = _load_corpus()
    if category not in c:
        return default
    val = c[category]
    # dict with subcategories → 随机选一个子分类
    if isinstance(val, dict):
        if sub and sub in val:
            items = val[sub]
            return random.choice(items) if items else default
        # 随机选任意子分类
        all_subs = [v for v in val.values() if v]
        if all_subs:
            chosen = random.choice(all_subs)
            return random.choice(chosen)
        return default
    # flat list
    if isinstance(val, list) and val:
        return random.choice(val)
    return default


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


def get_fallback_reply(emotion: str, intent: str = "", user_msg: str = "") -> str:
    """根据情绪和意图，从语料库选取人性化回复"""
    # 1. 意图优先匹配
    intent_categories = {
        "goodbye": ("goodbye", None),
        "thank_you": ("thank_you", None),
        "apology": ("apology", None),
        "morning": ("greetings", "morning"),
        "food": ("self_disclosure", None),
        "weather": ("self_disclosure", None),
        "joke": ("jokes", None),
        "riddle": ("riddles", None),
    }
    if intent and intent in intent_categories:
        cat, sub = intent_categories[intent]
        reply = _pick(cat, sub)
        if reply:
            return reply

    # 2. 情绪驱动选取
    routes = EMOTION_CORPUS_MAP.get(emotion, EMOTION_CORPUS_MAP["neutral"])
    for cat, sub in routes:
        reply = _pick(cat, sub)
        if reply:
            return reply

    # 3. 最终兜底
    return _pick("unknown") or "嗯～你说得对"


def get_api_fallback() -> str:
    """API 彻底失败时的兜底"""
    return _pick("self_disclosure") or _pick("unknown") or "嗯～我在呢"
