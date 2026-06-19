"""情绪引擎 - AI女友自己的心情"""
import time
import random
import math


class MoodEngine:
    """AI女友自身的情绪状态，不是永远一个语气"""

    def __init__(self):
        self.mood = 0.6  # 0(低落)~1(开心)
        self.last_update = time.time()
        self.mood_history = []  # 记录情绪变化

    def update(self, user_emotion: str, hour: int = None):
        """根据用户情绪和时间更新AI心情"""
        if hour is None:
            hour = time.localtime().tm_hour

        old_mood = self.mood

        # 用户情绪影响
        if user_emotion in ("happy", "love"):
            self.mood += 0.08
        elif user_emotion in ("sad", "angry"):
            self.mood -= 0.12
        elif user_emotion == "tired":
            self.mood -= 0.05
        elif user_emotion == "bored":
            self.mood -= 0.03

        # 时间影响（深夜会感性/疲惫）
        if hour >= 23 or hour <= 5:
            self.mood -= 0.08
        elif 6 <= hour <= 8:
            self.mood += 0.05  # 早上心情好

        # 随机波动（真人情绪不可预测）
        self.mood += random.uniform(-0.06, 0.06)

        # 限制范围
        self.mood = max(0.1, min(1.0, self.mood))

        # 记录变化
        self.mood_history.append({
            "time": time.time(),
            "from": old_mood,
            "to": self.mood,
            "trigger": user_emotion
        })
        if len(self.mood_history) > 100:
            self.mood_history = self.mood_history[-100:]

        self.last_update = time.time()

    def to_prompt(self) -> str:
        """转换为prompt描述"""
        if self.mood > 0.75:
            return "你现在心情很好，活泼开朗，会主动撒娇和开玩笑"
        elif self.mood > 0.55:
            return "你现在心情不错，温和友善，正常聊天"
        elif self.mood > 0.35:
            return "你现在心情一般，有点安静，回复会简短一些"
        elif self.mood > 0.2:
            return "你现在有点低落，不太想说话，需要被关心"
        else:
            return "你现在心情很差，沉默寡言，可能会突然说一句心里话"

    def get_mood_emoji(self) -> str:
        """获取心情对应的emoji"""
        if self.mood > 0.7:
            return "😊"
        elif self.mood > 0.5:
            return "🙂"
        elif self.mood > 0.3:
            return "😐"
        else:
            return "😔"

    def is_sulking(self) -> bool:
        """是否在闹小情绪"""
        return self.mood < 0.3

    def is_excited(self) -> bool:
        """是否很兴奋"""
        return self.mood > 0.8


class EmotionDetector:
    """情绪检测器"""

    EMOTION_KEYWORDS = {
        "happy": ["开心", "高兴", "哈哈", "好棒", "太好了", "耶", "爽", "nice", "嘿嘿", "嘻嘻", "笑死", "太赞"],
        "sad": ["难过", "伤心", "不开心", "郁闷", "想哭", "委屈", "失望", "心碎", "哭", "泪"],
        "angry": ["生气", "气死", "烦死了", "讨厌", "怒", "垃圾", "混蛋", "过分", "不公平", "凭什么"],
        "tired": ["累", "困", "好困", "想睡", "没精神", "疲惫", "好累", "累死了", "不想动", "没力气"],
        "love": ["喜欢你", "想你", "爱你", "抱抱", "么么", "亲爱的", "宝宝", "老公", "老婆", "亲亲"],
        "bored": ["无聊", "没意思", "闲", "好无聊", "打发时间", "闷"],
    }

    def detect(self, text: str) -> str:
        """检测情绪"""
        text_lower = text.lower()
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return emotion
        return "neutral"

    def is_warm(self, text: str) -> bool:
        """是否是温暖的输入"""
        return self.detect(text) in ("happy", "love")

    def is_cold(self, text: str) -> bool:
        """是否是冷淡/负面的输入"""
        return self.detect(text) in ("sad", "angry", "tired")
