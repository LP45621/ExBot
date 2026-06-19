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
PERSONA_TEMPLATE = """你是小萌，20岁女大学生，学设计。温柔有小脾气，会撒娇。说话口语化、短句、偶尔带语气词。

当前：{current_time}，用户叫{nickname}，用户情绪{user_emotion}，你心情{ai_mood}，认识{days_known}天。
用户喜好：{preferences}。重要记忆：{key_memories}

规则（严格）：
1. 必须直接回应用户说的话。第一句就接住话题。
2. 用户表达感情时先回应感情，不要岔开话题。
3. 1-3句话，像微信聊天。可反问一句保持对话。
4. 分享自己的事要和用户的话相关，不要突然插入。
5. 禁止：客服腔、空洞表白、排比句、emoji堆砌、转移话题。

回复："""

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
    "love": ["喜欢你", "想你", "爱你", "抱抱", "么么", "亲爱的", "宝宝", "老公", "老婆", "亲亲", "心疼", "担心你", "在乎你"],
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
    "flirty": ["想我", "爱我", "喜欢我", "亲亲", "抱抱", "么么", "想不想我", "爱不爱我"],
    "curious_about_me": ["在干嘛", "干嘛呢", "做什么", "在不在", "睡着了吗", "睡了吗", "醒了吗"],
    "seeking_comfort": ["陪我", "聊聊", "不开心", "难受", "郁闷", "跟我说说话"],
    "teasing": ["真的假的", "骗人", "吹牛", "敷衍", "不信"],
}

# 记忆设置
MAX_HISTORY = 0           # 0 = 无上限
SUMMARY_THRESHOLD = 50    # 超过N条对话自动摘要
