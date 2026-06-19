"""Token 压缩模块 - 无限历史 + 分级压缩"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "less_tokens_pkg"))

from less_tokens import smart_compress

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


def compress_message(message: str, level: str = "light") -> str:
    """压缩单条消息"""
    if not message or len(message) < 30:
        return message

    try:
        if level == "light":
            return smart_compress(message, **LIGHT_FLAGS)
        elif level == "medium":
            return smart_compress(message, **MEDIUM_FLAGS)
        elif level == "heavy":
            return smart_compress(message, **HEAVY_FLAGS)
        else:
            return message
    except Exception:
        return message


def compress_history(history: list) -> list:
    """压缩对话历史（无限长度，分级压缩）"""
    if not history:
        return history

    recent = COMPRESS_CONFIG["recent_count"]
    light = COMPRESS_CONFIG["light_count"]
    medium = COMPRESS_CONFIG["medium_count"]

    result = []
    for i, (role, content) in enumerate(history):
        total_idx = len(history) - 1 - i  # 从最新消息开始计数

        if total_idx < recent:
            # 最近的消息：完整保留
            result.append((role, content))
        elif total_idx < light:
            # 中期消息：轻度压缩
            compressed = compress_message(content, "light")
            result.append((role, compressed))
        elif total_idx < medium:
            # 远期消息：中度压缩
            compressed = compress_message(content, "medium")
            result.append((role, compressed))
        else:
            # 超远期：重度压缩
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
