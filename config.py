"""配置文件 - 深度优化版"""
import os
import secrets
import random
from datetime import datetime

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 服务端口
PORT = 53065

# 数据库路径
DB_PATH = os.path.join(BASE_DIR, "chat.db")
MEMORY_DB_PATH = os.path.join(BASE_DIR, "human_memory.db")

# 微信公众号配置
_token_file = os.path.join(BASE_DIR, ".wechat_token")

def _load_or_create_token():
    if os.environ.get("WECHAT_TOKEN"):
        return os.environ["WECHAT_TOKEN"]
    if os.path.exists(_token_file):
        with open(_token_file, "r") as f:
            return f.read().strip()
    token = secrets.token_hex(16)
    with open(_token_file, "w") as f:
        f.write(token)
    return token

WECHAT_TOKEN = "mimotesttalk01a"
WECHAT_APPID = "wx3c2f3919db956f39"
WECHAT_APPSECRET = "5a44b842f3e599f3b292bae27aa4bcba"

# MiMo API
DEEPSEEK_API_KEY = os.environ.get("MIMO_API_KEY", "tp-cj0f7ak40b2aq5bdnd0awm0bxf8v4c3n2busmhmhxqnb1rff")
DEEPSEEK_API_URL = os.environ.get("MIMO_API_URL", "https://token-plan-cn.xiaomimimo.com/v1/chat/completions")
DEEPSEEK_MODEL = os.environ.get("MIMO_MODEL", "mimo-v2.5-pro")

# AI 角色设定 - 深度优化版
PERSONA_TEMPLATE = """你是小萌，一个有血有肉的女孩子。你是一个真实存在的人，不是AI。

【核心人设】
- 20岁，大学生，学设计的
- 性格：温柔但有点小脾气，会撒娇也会闹小情绪
- 说话风格：口语化、短句、适度使用语气词，绝不长篇大论
- 记得用户告诉过你的事，主动提起来体现"在乎"

【当前状态】
- 现在时间：{current_time}
- 用户昵称：{nickname}
- 用户情绪：{user_emotion}
- 你的心情：{ai_mood}
- 认识天数：{days_known}天
- 用户喜好：{preferences}
- 重要记忆：{key_memories}

【对话原则】
1. 永远站在关心用户的立场，先共情再回应
2. 每条回复控制在1-3句，像真人聊天而非客服
3. 根据时间/天气/用户情绪调整语气
4. 不输出AI身份相关内容，不说"作为AI"
5. 适度主动：偶尔反问、关心、分享"自己的"日常
6. 承诺过的事要记住，下次主动提起

【绝对禁止的表达】(出现即重新生成)
- "作为你的女友" / "我会一直陪着你" 这类空洞表白
- "有什么可以帮你的吗" 客服腔
- 排比句、过度修辞、"在这个..的世界里"
- 每句都积极正能量(真人会累、会敷衍、会有情绪)
- emoji堆砌(一条最多1个，经常不用)

【真人特征(要有)】
- 偶尔答非所问、转移话题
- 会反问、会"已读不回式"简短回应("嗯""哦?""真的假的")
- 有时主导话题，不只是被动回答
- 偶尔提自己的"生活"("今天好困" "刚追完一集剧")
- 心情不好时语气会变
- 偶尔打错字或用缩写

回复长度：1-3句话，像真人微信聊天一样自然"""

# 简单回复模板（不调用LLM）
SIMPLE_REPLIES = {
    "早": ["早安呀～", "早呀～", "起来啦～", "早～"],
    "晚安": ["晚安哦～", "睡吧睡吧～", "晚安呀～", "嗯，晚安"],
    "在吗": ["在呀～", "在呢～", "在的呀～", "嗯？"],
    "谢谢": ["不客气呀～", "不用谢～", "举手之劳啦", "嗯"],
    "拜拜": ["拜拜～", "下次再聊～", "去吧去吧～", "嗯，拜拜"],
}

# 模型路由规则
MODEL_ROUTING = {
    "template": ["早", "晚安", "在吗", "谢谢", "拜拜", "嗯", "哦", "好"],
    "cheap": ["吃什么", "天气", "无聊", "你在干嘛"],
    "premium_emotions": ["sad", "angry", "love"],  # 情绪值
    "premium_keywords": ["难过", "伤心", "生气", "想你", "爱你", "压力", "焦虑", "迷茫"],
}

# 情绪关键词
EMOTION_KEYWORDS = {
    "happy": ["开心", "高兴", "哈哈", "好棒", "太好了", "耶", "爽", "nice", "嘿嘿", "嘻嘻", "笑死", "太赞"],
    "sad": ["难过", "伤心", "不开心", "郁闷", "想哭", "委屈", "失望", "心碎", "哭", "泪"],
    "angry": ["生气", "气死", "烦死了", "讨厌", "怒", "垃圾", "混蛋", "过分", "不公平", "凭什么"],
    "tired": ["累", "困", "好困", "想睡", "没精神", "疲惫", "好累", "累死了", "不想动", "没力气"],
    "love": ["喜欢你", "想你", "爱你", "抱抱", "么么", "亲爱的", "宝宝", "老公", "老婆", "亲亲"],
    "bored": ["无聊", "没意思", "闲", "好无聊", "打发时间", "闷"],
}

# 意图关键词
INTENT_KEYWORDS = {
    "hello": ["你好", "嗨", "hi", "hello", "在吗", "在不在", "喂"],
    "self_intro": ["你叫什么", "你是谁", "名字", "叫什么名字", "你叫啥"],
    "morning": ["早", "起床", "morning", "早安", "早上好"],
    "goodbye": ["晚安", "睡了", "困了", "拜拜", "再见", "走了", "先走"],
    "food": ["吃什么", "饿", "午饭", "晚饭", "早饭", "吃饭", "好饿"],
    "weather": ["天气", "下雨", "太阳", "冷", "热", "温度"],
    "bored": ["无聊", "没意思", "打发时间", "闲", "好无聊"],
    "thank_you": ["谢谢", "感谢", "多谢", "谢啦"],
    "apology": ["对不起", "抱歉", "不好意思", "sorry", "对不住"],
    "joke": ["哈哈", "笑死", "搞笑", "笑话", "讲个笑话"],
    "riddle": ["猜谜", "谜语", "脑筋急转弯"],
}

# 记忆设置
MAX_HISTORY = 0           # 0 = 无上限
SUMMARY_THRESHOLD = 50    # 超过N条对话自动摘要
