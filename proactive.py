"""主动消息系统 —— AI女友久不回复主动回话"""
import time
import random
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

# 兜底模板（大模型失败时使用）
FALLBACK_TEMPLATES = {
    "light": [
        "在干嘛呢～",
        "突然安静了，是去忙了吗？",
        "嗯？怎么不说话了",
        "在忙吗",
    ],
    "medium": [
        "这都半小时了，你在干嘛呀",
        "好久没理我了，是不是把我忘了",
        "刚才聊着聊着就不见了",
        "你去哪了呀",
    ],
    "deep": [
        "已经一个多小时了诶……刚才在忙什么重要的事嘛",
        "等你等了好久，不会又加班吧",
        "一个多小时没理我了……是不是我话太多啦",
        "你终于舍得回来了？我都快睡着了",
    ],
    "long": [
        "刚才看到一只超胖的橘猫，突然想到你～你忙完记得回我哦",
        "下午茶时间啦，你吃点东西了没",
        "好久没聊了，想你了",
    ],
}


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


def build_proactive_prompt(last_message: str, silence_minutes: int, level: str) -> str:
    """构建主动消息生成的Prompt"""
    time_ctx = get_time_context()
    
    level_instructions = {
        "light": "简短关心，不给他压力。1-2句话。",
        "medium": "结合他最后说的话追问一句，可以稍微撒娇。2-3句话。",
        "deep": "略带一丝埋怨但更多是担心，问他忙什么去了。2-3句话。",
        "long": "主动分享一个事或趣闻，给他台阶回来聊。2-3句话。",
    }
    
    return f"""你是一个细腻、粘人但有分寸的女友。

现在是{time_ctx}，距离男友上一次说话已经过去了{silence_minutes}分钟。
他最后说的话是：「{last_message}」

请生成一句主动问候（只输出纯文本，不加前缀）：
- {level_instructions.get(level, "简短关心。")}

硬性要求：
1. 自然带出时间概念（如"刚才"、"这都快一小时了"）
2. 字数严格控制在15-40字以内
3. 不要用句号，像微信气泡一样短
4. 不要用括号动作"""


async def generate_proactive_message(last_message: str, silence_minutes: int, level: str) -> str:
    """生成主动消息（优先用大模型，失败用模板）"""
    from ai import call_deepseek
    
    prompt = build_proactive_prompt(last_message, silence_minutes, level)
    messages = [{"role": "user", "content": prompt}]
    
    try:
        reply = await call_deepseek(messages, max_tokens=60)
        if reply and len(reply.strip()) > 2:
            return reply.strip()
    except Exception as e:
        logger.warning(f"Proactive message generation failed: {e}")
    
    # 兜底：随机模板
    templates = FALLBACK_TEMPLATES.get(level, FALLBACK_TEMPLATES["light"])
    return random.choice(templates)


async def check_and_generate_proactive(user_id: str) -> dict:
    """检查用户沉默状态，生成主动消息
    
    返回: {"should_send": bool, "message": str, "level": str, "silence_minutes": int}
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
    
    # 生成消息
    message = await generate_proactive_message(last_msg, minutes_ago, level)
    
    # 保存到待发送队列
    save_pending_message(user_id, message, minutes_ago, last_msg[:50])
    
    logger.info(f"Proactive message generated for {user_id[:8]}... "
                f"level={level}, silence={minutes_ago}min, msg={message[:30]}...")
    
    return {
        "should_send": True,
        "message": message,
        "level": level,
        "silence_minutes": minutes_ago,
        "created_at": now
    }


async def run_proactive_check():
    """后台定时任务：扫描所有活跃用户，检查是否需要主动消息"""
    from memory import get_user_info
    
    logger.info("Running proactive check...")
    
    # 获取所有有聊天记录的用户
    import sqlite3
    from config import DB_PATH
    
    conn = sqlite3.connect(DB_PATH, timeout=5)
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
        logger.info(f"Proactive check complete: {len(results)} messages generated")
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
