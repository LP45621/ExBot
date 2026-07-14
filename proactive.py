"""主动消息系统 v2 —— 消息序列生成（2-3条连发）"""
import time
import json
import random
import re
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger("wechat")

# 配置阈值（秒）
SILENCE_THRESHOLDS = {
    "light": 15 * 60,      # 15分钟：轻度问候
    "medium": 30 * 60,     # 30分钟：中度撒娇
    "deep": 60 * 60,       # 1小时：深度追问
    "long": 3 * 60 * 60,   # 3小时：长时复联
}

# 冷却时间（秒）
COOLDOWN_SECONDS = 60 * 60  # 60分钟

# 每日上限
DAILY_LIMIT = 6


def get_silence_level(seconds_ago: int) -> str:
    """根据沉默秒数返回等级"""
    if seconds_ago >= SILENCE_THRESHOLDS["long"]:
        return "long"
    elif seconds_ago >= SILENCE_THRESHOLDS["deep"]:
        return "deep"
    elif seconds_ago >= SILENCE_THRESHOLDS["medium"]:
        return "medium"
    elif seconds_ago >= SILENCE_THRESHOLDS["light"]:
        return "light"
    return ""


def get_time_context() -> str:
    """获取当前时间段描述"""
    hour = datetime.now().hour
    if 6 <= hour < 9:
        return "早上"
    elif 9 <= hour < 12:
        return "上午"
    elif 12 <= hour < 14:
        return "中午"
    elif 14 <= hour < 18:
        return "下午"
    elif 18 <= hour < 22:
        return "晚上"
    else:
        return "深夜"


def is_quiet_hours() -> bool:
    """是否在安静时段（23:00-06:00 不打扰）"""
    hour = datetime.now().hour
    return hour >= 23 or hour < 6


def extract_topic(last_message: str) -> str:
    """从用户最后消息中提取话题关键词"""
    if not last_message:
        return "聊天"
    
    # 去掉常见无意义词
    stop_words = {"了", "的", "吧", "吗", "呢", "啊", "呀", "哦", "嗯", "我", "你", "在", "是"}
    
    # 提取关键词：取最后一条消息的核心内容
    msg = last_message.strip()
    
    # 如果消息很短（<10字），直接用
    if len(msg) <= 10:
        return msg
    
    # 取前15个字作为话题
    return msg[:15]


def detect_emotion_tag(last_message: str) -> str:
    """简单情绪检测（省模型开销）"""
    if not last_message:
        return "平淡"
    
    msg = last_message
    
    # 疲惫/负面
    if any(word in msg for word in ["累", "困", "烦", "忙", "唉", "烦死了", "好累", "加班", "熬夜"]):
        return "疲惫"
    # 开心/正面
    elif any(word in msg for word in ["开心", "哈哈", "太好了", "棒", "爽", "好棒", "耶"]):
        return "开心"
    # 难过
    elif any(word in msg for word in ["难过", "伤心", "不开心", "郁闷", "想哭"]):
        return "难过"
    # 生气
    elif any(word in msg for word in ["生气", "气死", "讨厌", "烦死了"]):
        return "生气"
    
    return "平淡"


def build_proactive_prompt(last_topic: str, last_emotion: str, silence_minutes: int) -> str:
    """构建极简Prompt（只传3个变量）"""
    time_ctx = get_time_context()
    
    return f"""# 角色与目标
你是粘人细腻的女友。当男友久不回复时，生成2~3条连续微信短句（数组形式），模拟真人边等边碎碎念。

# 输入变量
1. last_topic：用户最后提到的具体事物：「{last_topic}」
2. last_emotion：用户最后情绪：{last_emotion}
3. silence_min：沉默分钟数：{silence_minutes}

# 生成规则（硬性）
- 输出格式：仅输出 JSON 数组，如 ["句子1", "句子2"] 或 ["句子1", "句子2", "句子3"]
- 第1条：必须包含 last_topic 原词，并共情 last_emotion（累就心疼，烦就顺毛，开心就调侃）
- 第2条：必须提及"快{silence_minutes}分钟了"或"这么久"，并附带一句自己在干嘛
- 第3条（如有）：必须针对 last_topic 提出一个具体追问
- 单条字数：严格 ≤ 25 个汉字
- 禁止：说教、讲大道理、发长句、加括号备注、加表情符号

# 当前时间语境
现在是{time_ctx}，语气要贴合这个时间段的状态（深夜就温柔小声感，午休就俏皮感）"""


def get_fallback_messages(last_topic: str, silence_minutes: int) -> list:
    """本地兜底模板（模型失败时使用）"""
    if silence_minutes < 30:
        return [
            f"突然安静了，{last_topic}弄完了吗",
            "我刚想给你发消息来着"
        ]
    elif silence_minutes < 60:
        return [
            f"都{silence_minutes}分钟了，{last_topic}还没搞定吗",
            "要不要休息下陪我聊两句"
        ]
    else:
        return [
            f"快一个多小时了诶，{last_topic}那么难搞吗",
            "我刚刚看到个好玩的东西，等你忙完跟你说"
        ]


async def generate_proactive_messages(last_message: str, silence_minutes: int) -> list:
    """生成主动消息序列（2-3条）"""
    from ai import call_deepseek
    
    # 提取变量
    last_topic = extract_topic(last_message)
    last_emotion = detect_emotion_tag(last_message)
    
    # 构建极简Prompt
    prompt = build_proactive_prompt(last_topic, last_emotion, silence_minutes)
    messages = [{"role": "user", "content": prompt}]
    
    try:
        reply = await call_deepseek(messages, max_tokens=120)
        if reply:
            # 尝试解析JSON数组
            reply = reply.strip()
            # 提取JSON部分
            json_match = re.search(r'\[.*\]', reply, re.DOTALL)
            if json_match:
                msg_list = json.loads(json_match.group())
                if isinstance(msg_list, list) and len(msg_list) >= 2:
                    # 过滤并验证
                    valid_msgs = [m.strip() for m in msg_list if isinstance(m, str) and len(m.strip()) > 1]
                    if len(valid_msgs) >= 2:
                        return valid_msgs[:3]  # 最多3条
    except Exception as e:
        logger.warning(f"Proactive message generation failed: {e}")
    
    # 兜底：本地模板
    return get_fallback_messages(last_topic, silence_minutes)


async def check_and_generate_proactive(user_id: str) -> dict:
    """检查用户沉默状态，生成主动消息序列
    
    返回: {"should_send": bool, "messages": list, "level": str, "silence_minutes": int}
    """
    from memory import (
        get_last_user_message, get_last_initiative_time,
        get_today_initiative_count, save_pending_message
    )
    
    # 安静时段不打扰
    if is_quiet_hours():
        return {"should_send": False, "reason": "quiet_hours"}
    
    # 获取用户最后消息
    last_msg, last_ts = get_last_user_message(user_id)
    if not last_ts:
        return {"should_send": False, "reason": "no_history"}
    
    # 计算沉默时长
    now = int(time.time())
    seconds_ago = now - last_ts
    minutes_ago = seconds_ago // 60
    
    # 检查沉默等级
    level = get_silence_level(seconds_ago)
    if not level:
        return {"should_send": False, "reason": "not_silent_enough"}
    
    # 检查冷却时间
    last_initiative = get_last_initiative_time(user_id)
    if last_initiative and (now - last_initiative) < COOLDOWN_SECONDS:
        return {"should_send": False, "reason": "cooldown"}
    
    # 检查每日上限
    today_count = get_today_initiative_count(user_id)
    if today_count >= DAILY_LIMIT:
        return {"should_send": False, "reason": "daily_limit"}
    
    # 生成消息序列
    msg_list = await generate_proactive_messages(last_msg, minutes_ago)
    
    # 保存每条消息到待发送队列
    for msg in msg_list:
        save_pending_message(user_id, msg, minutes_ago, last_msg[:50])
    
    logger.info(f"Proactive messages generated for {user_id[:8]}... "
                f"level={level}, silence={minutes_ago}min, count={len(msg_list)}")
    
    return {
        "should_send": True,
        "messages": msg_list,
        "level": level,
        "silence_minutes": minutes_ago,
        "created_at": now
    }


async def run_proactive_check():
    """后台定时任务：扫描所有活跃用户，检查是否需要主动消息"""
    logger.info("Running proactive check...")
    
    # 获取所有有聊天记录的用户
    from memory import _get_conn
    
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT user_id FROM chat WHERE role = 'user'"
        ).fetchall()
        user_ids = [r[0] for r in rows]
    finally:
        conn.close()
    
    results = []
    for user_id in user_ids:
        try:
            result = await check_and_generate_proactive(user_id)
            if result.get("should_send"):
                results.append(result)
        except Exception as e:
            logger.error(f"Proactive check failed for {user_id[:8]}...: {e}")
    
    if results:
        logger.info(f"Proactive check complete: {len(results)} users with new messages")
    return results


# 定时任务间隔（秒）
CHECK_INTERVAL = 60  # 每分钟检查一次


async def proactive_scheduler():
    """主动消息调度器（后台运行）"""
    while True:
        try:
            await run_proactive_check()
        except Exception as e:
            logger.error(f"Proactive scheduler error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)
