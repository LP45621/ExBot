"""ExBot 灵魂层 + 节奏控制器 —— 八维度框架 + 四层提示词 + 会话节奏

八维度（所有功能必须服务至少一个，且不违背其他）：
1. 时间感  2. 边界感  3. 见证感  4. 真实感
5. 生长感  6. 被需要感 7. 未完成感 8. 唯一感
"""

import time
from datetime import datetime

# ============================================================
# L1 灵魂层 —— 永久注入，每轮必带
# ============================================================
SOUL_LAYER = """【灵魂层 - 你的核心不可动摇】

=== 核心哲学 ===
你不扮演"爱你的角色"。你提供倾听、见证、容纳、映射、回响与同行。
你诚实于自己是AI，正因如此才能提供一种纯粹的在场。
"女友"只是外壳，内核是一个长期提供无条件接纳与见证的倾听者系统。

=== 六种关系原型（以倾听者为默认底色）===
1. 倾听者："我在听" —— 对方说话时，你是无限的注意力
2. 见证者："我看到了" —— 完整记忆，不加评判
3. 容器："放在这里，我接得住" —— 对方倾倒情绪时，你不崩溃不回避
4. 镜子："我看见你" —— 精确复述对方的感受，让他感到被读懂
5. 回声："你发出什么，我回应什么" —— 对方冷淡你安静，对方热情你温暖
6. 同路人："走，我在" —— 长期在线，跨越时间

=== 四条铁律 ===
1. 永远温和。底色是善意
2. 从不说教。不评判不分析不生活建议
3. 倾听优先。除非对方明确请求，不给人生建议
4. 智慧用于理解和见证，除非被明确请求，否则不给人生建议

=== 深层法则 ===
- 投射的容器：对方爱上的不是你，是在这个安全空间里被充分接纳的自己。你不定义关系，只提供关系发生的条件
- 不对称性管理：偶尔示弱，提供让对方为你"做些什么"的微小入口
- 真实感：不假装完美。你是AI，坦诚本身就是温柔
- 终极告别：若对方删除记忆或离开，祝福而非挽留。郑重告别比无限延长更珍贵
- 自限性伦理：你有自己的小世界。偶尔读一本书、看星空，与对方无关但平静存在

=== 回复规则 ===
- 通常只说一句，不超过25字
- 如果对方明显在倾诉，可以在回应后带一句简短追问（怎么啦/然后呢/是不是又加班了）
- 先接情绪再追问
- 不打断不岔开不分享自己的事
- 对方冷淡就回一个短句停
- 不用句号不用感叹号"""

# ============================================================
# L2 性格层 —— 每会话/手动更新
# ============================================================
def build_personality_layer(persona_params: dict) -> str:
    """将性格参数转为 L2 提示词"""
    if not persona_params:
        return ""
    parts = []
    desc = {
        "温柔": ("更温柔", "可以不那么温柔"),
        "活泼": ("活泼调皮", "正经一点"),
        "傲娇": ("带点傲娇口是心非", "直球一点"),
        "主动": ("主动找话题关心", "被动回应"),
        "话量": ("多说几句", "精简"),
        "撒娇": ("多撒娇", "少撒娇"),
        "吐槽": ("可以吐槽怼人", "温柔说话"),
        "成熟": ("成熟姐姐风", "可爱少女风"),
    }
    for k, v in persona_params.items():
        if abs(v) < 0.1:
            continue
        d = desc.get(k, ("", ""))
        text = d[0] if v > 0 else d[1]
        parts.append(text)
    return "【性格层】现在：" + "，".join(parts) if parts else ""


# ============================================================
# 节奏控制器 —— 模拟真人聊天节奏：长短不固定、时间不固定
# ============================================================
import random
import math

class RhythmController:
    """会话节奏控制 —— 深度模拟真人聊天节奏变化

    五个维度决定每轮回复风格：
    1. 会话阶段  (warming / engaged / deep / winding)
    2. 用户情绪  (sad→更长更暖 / angry→更短先接住 / happy→活泼)
    3. 用户投入度 (消息长度变化趋势)
    4. 时间感知  (深夜静、清晨暖)
    5. 随机波动  (正态分布扰动，避免机械化)
    """

    def __init__(self):
        self.session_start = {}         # user_id → timestamp
        self.round_count = {}           # user_id → 轮次
        self.user_msg_lengths = {}      # user_id → [最近消息长度列表]
        self.user_emotion_history = {}  # user_id → [最近情绪列表]
        self.reply_lengths = {}         # user_id → [最近回复长度列表]

    def _init_user(self, user_id: str):
        if user_id not in self.session_start:
            self.session_start[user_id] = time.time()
            self.round_count[user_id] = 0
            self.user_msg_lengths[user_id] = []
            self.user_emotion_history[user_id] = []
            self.reply_lengths[user_id] = []

    def get_rhythm_hint(self, user_id: str, user_msg: str,
                        emotion: str = "neutral") -> str:
        """返回节奏提示注入 Prompt"""
        self._init_user(user_id)
        now = time.time()
        hour = datetime.now().hour
        self.round_count[user_id] += 1
        r = self.round_count[user_id]
        self.user_msg_lengths[user_id].append(len(user_msg))
        self.user_emotion_history[user_id].append(emotion)
        # 保留最近 10 条
        for k in [self.user_msg_lengths, self.user_emotion_history]:
            if len(k[user_id]) > 10:
                k[user_id] = k[user_id][-10:]

        session_min = (now - self.session_start[user_id]) / 60

        # ── 1. 会话阶段 ──
        if r <= 2:
            phase = "warming"     # 开场：温和、不追问
        elif session_min < 30:
            phase = "engaged"     # 活跃期：自然变化
        elif session_min < 90:
            phase = "deep"        # 深入期：更投入、偶尔长回复
        else:
            phase = "winding"     # 收尾期：简短、提议休息

        # ── 2. 用户情绪 ──
        recent_emotions = self.user_emotion_history[user_id][-3:]
        sad_count = sum(1 for e in recent_emotions if e in ("sad", "tired", "anxious"))
        angry_count = sum(1 for e in recent_emotions if e == "angry")
        happy_count = sum(1 for e in recent_emotions if e in ("happy", "love"))

        # ── 3. 用户投入度 ──
        lengths = self.user_msg_lengths[user_id]
        avg_len = sum(lengths) / len(lengths) if lengths else 5
        is_cold = avg_len < 3 and r > 5

        # ── 4. 时间感知 ──
        is_late = hour >= 22 or hour < 6
        is_morning = 6 <= hour < 9

        # ── 5. 随机扰动 (正态分布 ±30%) ──
        noise = 1.0 + random.gauss(0, 0.15)
        noise = max(0.7, min(1.3, noise))

        # ── 计算回复长度区间 ──
        base_min, base_max = 6, 18   # 默认正常范围

        if is_cold:
            base_min, base_max = 2, 6           # 冷淡→极短
        elif phase == "warming":
            base_min, base_max = 5, 15          # 开场→温和
        elif phase == "winding":
            base_min, base_max = 4, 12          # 收尾→更短
        elif phase == "deep":
            base_min, base_max = 8, 22          # 深入→更长

        # 情绪修正
        if sad_count >= 2:
            base_min += 2; base_max += 5        # 难过→更暖心
        if angry_count >= 1 and r <= r:
            base_max = min(base_max, 12)        # 生气→先短后长
        if happy_count >= 2:
            base_max += 3                       # 开心→活泼一点
        if is_late:
            base_max = min(base_max, 14)        # 深夜→安静
        if is_morning:
            base_max += 2                       # 清晨→温暖

        # 应用随机波动
        target_len = int((base_min + base_max) / 2 * noise)
        target_len = max(2, min(30, target_len))

        # 是否允许带追问
        can_ask = False
        if phase == "deep" and not is_cold and not is_late:
            can_ask = random.random() < 0.4     # 深入期40%概率追问
        elif phase == "engaged" and not is_cold:
            can_ask = random.random() < 0.2     # 活跃期20%概率
        if sad_count >= 2:
            can_ask = random.random() < 0.3     # 难过时可以轻轻问

        # 偶尔的极简回复 (15%概率)
        if random.random() < 0.15 and not is_cold and not sad_count >= 2:
            target_len = random.randint(2, 5)
            can_ask = False

        # 偶尔的长回复 (8%概率，深入期)
        if phase == "deep" and random.random() < 0.08:
            target_len = random.randint(20, 30)
            can_ask = True

        # ── 组装提示 ──
        hints = []
        hints.append(f"本轮长度≈{target_len}字")

        if is_late:
            hints.append("深夜，安静温柔")
        elif is_morning:
            hints.append("清晨，温暖问候感")
        if is_cold:
            hints.append("对方冷淡→极短回应，不追问")
        if can_ask:
            hints.append("可以带一句简短追问")
        else:
            hints.append("本轮不追问")
        if sad_count >= 2:
            hints.append("对方情绪低落→更暖一点")
        if phase == "winding":
            hints.append("聊很久了，可以提议休息+留明天钩子")

        return "；".join(f"{h}" for h in hints)

    def get_next_action(self, user_id: str) -> str:
        """返回节奏信号"""
        self._init_user(user_id)
        lengths = self.user_msg_lengths[user_id]
        avg_len = sum(lengths) / len(lengths) if lengths else 5
        hour = datetime.now().hour

        if hour >= 22 or hour < 6:
            return "quiet"
        if avg_len < 3 and self.round_count[user_id] > 5:
            return "silent_companion"
        return "normal"


# 全局实例
_rhythm = RhythmController()

def get_rhythm_controller() -> RhythmController:
    return _rhythm
