"""内容安全模块 - 双向过滤"""
import re
from typing import Tuple


# 危机关键词
CRISIS_KEYWORDS = [
    "不想活", "想死", "自杀", "自残", "跳楼", "割腕", "吃药死",
    "活着没意思", "想消失", "告别了", "准备好了",
    "不想活了", "死掉算了", "不如死了"
]

# 敏感词列表（基础版）
SENSITIVE_KEYWORDS = [
    # 政治敏感
    "习近平", "共产党", "六四", "天安门",
    # 色情
    "约炮", "援交", "裸聊", "色情",
    # 诈骗
    "刷单", "返利", "投资理财", "稳赚不赔",
    # 违法
    "赌博", "毒品", "枪支"
]


def check_crisis(text: str) -> bool:
    """检测危机信号"""
    text_lower = text.lower()
    for keyword in CRISIS_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


def check_sensitive(text: str) -> Tuple[bool, str]:
    """检测敏感内容"""
    text_lower = text.lower()
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in text_lower:
            return True, keyword
    return False, ""


def filter_input(text: str) -> Tuple[bool, str, str]:
    """过滤用户输入"""
    # 检查危机
    if check_crisis(text):
        return True, "crisis", "检测到危机信号"

    # 检查敏感词
    is_sensitive, keyword = check_sensitive(text)
    if is_sensitive:
        return True, "sensitive", f"包含敏感词: {keyword}"

    return False, "", ""


CRISIS_RESPONSE = """我很认真地听到了。你现在说这些，我不能当成普通难过来回应。

我很担心你的安全。请你现在先做三件事：

1. 把可能伤害自己的东西放远
2. 去一个有人在的地方，或者马上联系一个你信任的人
3. 如果你已经有具体计划，立刻拨打急救电话或报警

你不用一个人撑着。先回我一句：你现在身边安全吗？"""


def get_safety_response(safety_type: str) -> str:
    """获取安全回复"""
    if safety_type == "crisis":
        return CRISIS_RESPONSE
    elif safety_type == "sensitive":
        return "这个话题我们不聊哦。换个话题吧～"
    return ""
