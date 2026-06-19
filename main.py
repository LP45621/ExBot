"""微信公众号 AI 陪伴助手 - 最终优化版"""
import hashlib
import time
import uuid
import random
import logging
import asyncio
import defusedxml.ElementTree as ET
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from config import WECHAT_TOKEN, PORT
from ai import get_ai_reply
from engine import split_reply
from safety import filter_input, get_safety_response, check_crisis

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wechat")

# 全局状态
_rate_limit = defaultdict(list)
RATE_LIMIT = 10
RATE_WINDOW = 60
_last_cleanup = time.time()
MAX_MSG_LENGTH = 500
MAX_BODY_SIZE = 10240

# 消息去重缓存
_dedup_cache = {}
_dedup_last_clean = time.time()

# 服务统计
_stats = {
    "total_requests": 0,
    "total_messages": 0,
    "total_errors": 0,
    "total_crisis": 0,
    "start_time": time.time()
}


def verify_signature(token: str, signature: str, timestamp: str, nonce: str) -> bool:
    """验证微信签名"""
    if not all([token, signature, timestamp, nonce]):
        return False
    try:
        items = sorted([token, timestamp, nonce])
        return hashlib.sha1("".join(items).encode()).hexdigest() == signature
    except Exception:
        return False


def cleanup_rate_limit():
    """清理过期的速率限制记录"""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < 300:
        return
    _last_cleanup = now
    expired = [uid for uid, times in _rate_limit.items()
               if not any(now - t < RATE_WINDOW for t in times)]
    for uid in expired:
        del _rate_limit[uid]


def check_rate_limit(user_id: str) -> bool:
    """检查速率限制"""
    now = time.time()
    _rate_limit[user_id] = [t for t in _rate_limit[user_id] if now - t < RATE_WINDOW]
    if len(_rate_limit[user_id]) >= RATE_LIMIT:
        return False
    _rate_limit[user_id].append(now)
    return True


def check_duplicate(body: bytes) -> bool:
    """检查消息是否重复"""
    global _dedup_last_clean
    now = time.time()

    if now - _dedup_last_clean > 300:
        _dedup_cache.clear()
        _dedup_last_clean = now

    msg_hash = hashlib.md5(body).hexdigest()
    if msg_hash in _dedup_cache:
        return True
    _dedup_cache[msg_hash] = now
    return False


app = FastAPI(title="微信AI陪伴助手")


@app.get("/wechat")
async def verify(request: Request):
    """微信服务器验证"""
    params = request.query_params
    sig = params.get("signature", "")
    ts = params.get("timestamp", "")
    nonce = params.get("nonce", "")
    echostr = params.get("echostr", "")

    if not sig or not ts or not nonce:
        return PlainTextResponse("error")

    if verify_signature(WECHAT_TOKEN, sig, ts, nonce):
        return PlainTextResponse(echostr)

    return PlainTextResponse("error")


@app.post("/wechat")
async def handle_message(request: Request):
    """处理微信消息"""
    cleanup_rate_limit()
    _stats["total_requests"] += 1
    request_id = uuid.uuid4().hex[:8]

    try:
        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            return PlainTextResponse("success")

        if check_duplicate(body):
            logger.info(f"[{request_id}] Duplicate message, skip")
            return PlainTextResponse("success")

        root = ET.fromstring(body)
        msg_type = root.findtext("MsgType", "")
        user_id = root.findtext("FromUserName", "")
        to_user = root.findtext("ToUserName", "")

        if not user_id or not to_user:
            return PlainTextResponse("success")

        if not check_rate_limit(user_id):
            return PlainTextResponse("success")

        if msg_type == "text":
            content = root.findtext("Content", "").strip()
            if not content:
                reply = "你怎么不说话呀～"
            elif len(content) > MAX_MSG_LENGTH:
                reply = "消息太长啦～缩短一点告诉我嘛～"
            else:
                # 内容安全检查
                is_unsafe, safety_type, reason = filter_input(content)
                if is_unsafe:
                    reply = get_safety_response(safety_type)
                    _stats["total_crisis"] += 1
                    logger.warning(f"[{request_id}] Safety alert: {reason}")
                else:
                    logger.info(f"[{request_id}] User {user_id[:8]}...: {content[:30]}")
                    reply = await get_ai_reply(user_id, content, request_id)
                    logger.info(f"[{request_id}] AI reply: {reply[:30]}")
                    _stats["total_messages"] += 1
        elif msg_type == "image":
            reply = "图片收到啦～但我暂时只看得懂文字，你可以用文字告诉我你想说什么嘛～"
        elif msg_type == "voice":
            reply = "语音收到啦～但我暂时听不懂，你可以打字告诉我嘛～"
        elif msg_type == "video":
            reply = "视频收到啦～好可惜我暂时看不懂视频呢"
        else:
            reply = "收到啦～但我只看得懂文字消息哦～"

        timestamp = str(int(time.time()))
        xml_response = f"""<xml>
<ToUserName><![CDATA[{user_id}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply}]]></Content>
</xml>"""

        return PlainTextResponse(xml_response, media_type="application/xml")

    except ET.ParseError as e:
        logger.error(f"[{request_id}] XML parse error: {e}")
        _stats["total_errors"] += 1
        return PlainTextResponse("success")
    except Exception as e:
        logger.error(f"[{request_id}] Handle message error: {e}", exc_info=True)
        _stats["total_errors"] += 1
        return PlainTextResponse("success")


@app.get("/health")
async def health():
    """健康检查"""
    import sqlite3
    import os
    from config import DB_PATH as CHAT_DB
    from script_db import DB_PATH as SCRIPT_DB

    db_ok = False
    conn = None
    try:
        conn = sqlite3.connect(CHAT_DB, timeout=2)
        conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    scripts_ok = os.path.exists(SCRIPT_DB)
    uptime = time.time() - _stats["start_time"]

    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "scripts": scripts_ok,
        "uptime": round(uptime, 1),
        "stats": _stats,
        "time": time.time()
    }


@app.get("/debug")
async def debug():
    """调试面板"""
    from engine import _mood_engine, get_memory_system

    mood = _mood_engine
    memory = get_memory_system()

    return {
        "mood": {
            "current": round(mood.mood, 2),
            "description": mood.to_prompt(),
            "emoji": mood.get_mood_emoji(),
            "is_sulking": mood.is_sulking(),
            "is_excited": mood.is_excited(),
            "history_count": len(mood.mood_history)
        },
        "stats": _stats,
        "rate_limit_users": len(_rate_limit),
        "dedup_cache_size": len(_dedup_cache)
    }


@app.on_event("startup")
async def startup():
    logger.info("Starting WeChat AI Companion Server...")
    from script_db import DB_PATH as SCRIPT_DB
    import os
    if not os.path.exists(SCRIPT_DB):
        logger.info("Initializing scripts database...")
        from script_db import init_db
        init_db()
    logger.info("Server ready!")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down server...")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
