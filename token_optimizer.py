"""Token 压缩模块 - 分级压缩（可选依赖 less_tokens）"""
import os

# less_tokens 为可选依赖，不可用时使用基础压缩
try:
    from less_tokens import smart_compress
    HAS_SMART_COMPRESS = True
except ImportError:
    HAS_SMART_COMPRESS = False

# 压缩级别配置
COMPRESS_CONFIG = {
    "recent_count": 15,      # 最近 N 条不压缩
    "light_count": 50,       # 15-N 条轻度压缩
    "medium_count": 200,     # 50-N 条中度压缩
    # 200+ 条：重度压缩
}

LIGHT_FLAGS = {
    "remove_filler_phrases": 1,
    "remove_stopwords": 0,
    "apply_contractions": 0,
}

MEDIUM_FLAGS = {
    "remove_filler_phrases": 1,
    "remove_stopwords": 1,
    "apply_contractions": 0,
}

HEAVY_FLAGS = {
    "remove_filler_phrases": 1,
    "remove_stopwords": 1,
    "apply_contractions": 1,
}

_FILLER_PHRASES = ["嗯嗯", "然后呢", "就是说", "其实", "那个", "怎么说呢"]


def _basic_compress(message: str, level: str = "light") -> str:
    """基础压缩：去除冗余标点和填充词"""
    if not message:
        return message
    # 去除重复标点
    import re
    msg = re.sub(r'[。！？]{2,}', '。', message)
    msg = re.sub(r'[~～]{2,}', '～', msg)
    if level in ("medium", "heavy"):
        for filler in _FILLER_PHRASES:
            msg = msg.replace(filler, "")
    if level == "heavy" and len(msg) > 60:
        msg = msg[:60] + "..."
    return msg.strip() or message


def compress_message(message: str, level: str = "light") -> str:
    """压缩单条消息"""
    if not message or len(message) < 30:
        return message
    try:
        if HAS_SMART_COMPRESS:
            flags = {"light": LIGHT_FLAGS, "medium": MEDIUM_FLAGS, "heavy": HEAVY_FLAGS}
            return smart_compress(message, **flags.get(level, LIGHT_FLAGS))
        return _basic_compress(message, level)
    except Exception:
        return _basic_compress(message, level)


def compress_history(history: list) -> list:
    """压缩对话历史（无限长度，分级压缩）"""
    if not history:
        return history

    recent = COMPRESS_CONFIG["recent_count"]
    light = COMPRESS_CONFIG["light_count"]
    medium = COMPRESS_CONFIG["medium_count"]

    result = []
    for i, (role, content) in enumerate(history):
        total_idx = len(history) - 1 - i

        if total_idx < recent:
            result.append((role, content))
        elif total_idx < light:
            result.append((role, compress_message(content, "light")))
        elif total_idx < medium:
            result.append((role, compress_message(content, "medium")))
        else:
            compressed = compress_message(content, "heavy")
            if compressed and len(compressed) > 10:
                result.append((role, compressed))

    return result


def get_compression_stats(original: list, compressed: list) -> dict:
    """获取压缩统计"""
    orig_len = sum(len(c) for _, c in original)
    comp_len = sum(len(c) for _, c in compressed)
    saved = orig_len - comp_len
    ratio = saved / orig_len if orig_len > 0 else 0
    return {
        "original_messages": len(original),
        "compressed_messages": len(compressed),
        "original_chars": orig_len,
        "compressed_chars": comp_len,
        "chars_saved": saved,
        "compression_ratio": f"{ratio:.1%}"
    }


def estimate_tokens(text: str) -> int:
    """估算 token 数量（粗略：1个中文字≈2token，1个英文词≈1.3token）"""
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 2 + other_chars * 0.3)
