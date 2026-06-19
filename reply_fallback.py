"""灾备兜底 —— 仅在 DeepSeek API 彻底不可用时使用"""
import json
import random
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "scripts.json")

_CORPUS = None

def _load_corpus():
    global _CORPUS
    if _CORPUS is None:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            _CORPUS = json.load(f)
    return _CORPUS


def get_api_fallback() -> str:
    """DeepSeek API 完全崩溃时的最低兜底"""
    c = _load_corpus()
    items = c.get("emergency_fallback", ["嗯 我在"])
    return random.choice(items)


def get_fallback_reply(emotion: str = "", intent: str = "",
                       user_msg: str = "", user_id: str = "") -> str:
    """兼容旧接口，统一走灾备兜底"""
    return get_api_fallback()
