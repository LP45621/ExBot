"""灾备兜底 —— 仅在 API 彻底不可用时使用"""
import random

_FALLBACKS = [
    "嗯 我在",
    "怎么啦",
    "我在呢",
    "嗯嗯",
    "说吧",
    "你说",
    "我听着呢",
    "嗯？",
    "怎么了",
    "在的",
]


def get_api_fallback() -> str:
    """API 完全崩溃时的最低兜底"""
    return random.choice(_FALLBACKS)


def get_fallback_reply(emotion: str = "", intent: str = "",
                       user_msg: str = "", user_id: str = "") -> str:
    """兼容旧接口，统一走兜底"""
    return get_api_fallback()
