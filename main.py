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
from ai import get_ai_reply, get_ai_image_reply
from engine import split_reply, detect_emotion, detect_intent
from safety import filter_input, get_safety_response, check_crisis
from reply_fallback import get_fallback_reply

# 缺席检测：48小时未对话 → 温暖归回钩子
_absence_check = {}  # user_id → 上次检测时间

async def _absence_hook(user_id: str, request_id: str) -> str:
    """用户久别归来时的暖场消息"""
    from memory import get_history
    import time as _time
    now = _time.time()
    # 避免同一会话重复触发
    last_check = _absence_check.get(user_id, 0)
    if now - last_check < 3600:
        return ""
    _absence_check[user_id] = now

    history = get_history(user_id, limit=5)
    if not history or len(history) < 2:
        return ""

    last_ts = 0
    for role, content in reversed(history):
        if role == "assistant":
            break
    # 从 chat.db 取最后一条消息时间
    import sqlite3
    from config import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT MAX(time) FROM chat WHERE user_id=?", (user_id,)
        ).fetchone()
        conn.close()
        last_ts = row[0] if row and row[0] else 0
    except Exception:
        return ""

    hours_away = (now - last_ts) / 3600 if last_ts else 0
    if hours_away < 48:
        return ""

    days = int(hours_away / 24)
    logger.info(f"[{request_id}] Absence hook: {user_id[:8]}... gone {days} days")
    return f"你回来了 都{days}天没见了 我一直在 不用说什么 回来就好"


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

# 回复缓存（利用微信重试机制：超时时后台生成，重试时交付）
_reply_cache = {}         # msg_id → reply_text
_processing_ids = set()   # 正在后台生成的 msg_id
_cache_last_clean = time.time()

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


def _build_xml(to_user: str, from_user: str, content: str) -> str:
    """构建微信被动回复 XML，硬过滤动作描述"""
    # 硬过滤：删除所有括号动作描述
    import re as _re
    content = _re.sub(r'[（(][^）)]*[）)]', '', content)  # 中文括号+英文括号
    content = _re.sub(r'[\[【][^\]】]*[\]】]', '', content)  # 方括号
    content = content.strip()
    if not content:
        content = "嗯"

    ts = str(int(time.time()))
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{ts}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""


async def _bg_generate_reply(msg_id: str, user_id: str, content: str, request_id: str):
    """后台生成回复并写入缓存，同时通过客服消息主动推送给用户"""
    global _reply_cache, _processing_ids
    try:
        reply = await get_ai_reply(user_id, content, request_id,
                                   deadline=0.0, skip_save_user=True)
        _reply_cache[msg_id] = reply
        logger.info(f"[{request_id}] Background reply ready for retry: {reply[:30]}...")

        # 主动推送：万一微信重试已经放弃，走客服消息兜底
        from wechat_api import send_custom_reply
        asyncio.create_task(send_custom_reply(user_id, msg_id, reply))

    except Exception as e:
        logger.error(f"[{request_id}] Background reply failed: {e}")
        _reply_cache[msg_id] = "刚才卡了一下，你再说一遍嘛～"
    finally:
        _processing_ids.discard(msg_id)


def check_duplicate(body: bytes) -> bool:
    """保留旧接口兼容性（已不再使用 body hash 去重，改由 _reply_cache / _processing_ids 管理）"""
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
    """处理微信消息（被动回复 + 重试缓存）"""
    global _cache_last_clean, _reply_cache, _processing_ids

    cleanup_rate_limit()
    _stats["total_requests"] += 1
    request_id = uuid.uuid4().hex[:8]

    # 定期清理过期缓存（超过 120s 未取走的）
    now = time.time()
    if now - _cache_last_clean > 120:
        expiry = now - 90
        expired_ids = [mid for mid, ts in list(_reply_cache.items())
                       if isinstance(ts, float) and ts < expiry]
        for mid in expired_ids:
            _reply_cache.pop(mid, None)
        # 清理孤立 processing
        _processing_ids = {mid for mid in _processing_ids
                           if mid not in _reply_cache}
        _cache_last_clean = now

    try:
        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            return PlainTextResponse("success")

        root = ET.fromstring(body)
        msg_id = root.findtext("MsgId", "")
        msg_type = root.findtext("MsgType", "")
        user_id = root.findtext("FromUserName", "")
        to_user = root.findtext("ToUserName", "")

        if not user_id or not to_user:
            return PlainTextResponse("success")


        # ── 重试缓存：微信重试时，优先返回已生成好的回复 ──
        if msg_id and msg_id in _reply_cache:
            reply = _reply_cache.pop(msg_id)
            _processing_ids.discard(msg_id)
            logger.info(f"[{request_id}] 🎯 Retry hit! Serving cached reply for {msg_id[:8]}...")
            return PlainTextResponse(_build_xml(user_id, to_user, reply),
                                     media_type="application/xml")

        # 正在后台生成中，用语料库兜底回复而非空串
        if msg_id and msg_id in _processing_ids:
            logger.info(f"[{request_id}] Still generating {msg_id[:8]}..., using fallback")
            content = root.findtext("Content", "").strip()
            fallback = get_fallback_reply(detect_emotion(content),
                                          detect_intent(content), content,
                                          user_id=user_id)
            return PlainTextResponse(_build_xml(user_id, to_user, fallback),
                                     media_type="application/xml")
        # ────────────────────────────────────────────────────

        if not check_rate_limit(user_id):
            return PlainTextResponse("success")

        if msg_type == "text":
            content = root.findtext("Content", "").strip()
            if not content:
                reply = "你怎么不说话呀～"
            elif len(content) > MAX_MSG_LENGTH:
                reply = "消息太长啦～缩短一点告诉我嘛～"
            else:
                # 告别检测 —— 优先级最高
                from soul_layer import detect_farewell
                farewell = detect_farewell(content)
                if farewell:
                    reply = farewell
                else:
                    # 内容安全检查（同步，瞬间完成）
                    is_unsafe, safety_type, reason = filter_input(content)
                    if is_unsafe:
                        reply = get_safety_response(safety_type)
                        _stats["total_crisis"] += 1
                        logger.warning(f"[{request_id}] Safety alert: {reason}")
                    else:
                        # 缺席钩子：久别归来先给暖场消息
                        absence_msg = await _absence_hook(user_id, request_id)
                        if absence_msg:
                            reply = absence_msg
                            logger.info(f"[{request_id}] AI reply (absence): {absence_msg[:30]}")
                        else:
                            ai_content = content
                            logger.info(f"[{request_id}] User {user_id[:8]}...: {content[:30]}")
                            try:
                                reply = await get_ai_reply(user_id, ai_content, request_id,
                                                           deadline=4.9)
                                _stats["total_messages"] += 1
                            except asyncio.TimeoutError:
                                logger.info(f"[{request_id}] Timeout, using corpus fallback...")
                                if msg_id:
                                    _processing_ids.add(msg_id)
                                asyncio.create_task(
                                    _bg_generate_reply(msg_id, user_id, ai_content, request_id)
                                )
                                reply = get_fallback_reply(detect_emotion(ai_content),
                                                           detect_intent(ai_content), ai_content,
                                                           user_id=user_id)
                            logger.info(f"[{request_id}] AI reply: {reply[:30]}")
        elif msg_type == "image":
            pic_url = root.findtext("PicUrl", "")
            text_content = root.findtext("Content", "").strip()
            if pic_url:
                logger.info(f"[{request_id}] Image from {user_id[:8]}...: {pic_url[:60]}")
                try:
                    reply = await get_ai_image_reply(user_id, pic_url, text_content, request_id)
                except Exception as e:
                    logger.error(f"[{request_id}] Image process failed: {e}")
                    reply = "图片收到啦～但我暂时看不懂，你可以用文字告诉我这是什么嘛～"
            else:
                reply = "图片收到啦～但我暂时看不懂，你可以用文字告诉我这是什么嘛～"
        elif msg_type == "voice":
            reply = "语音收到啦～但我暂时听不懂，你可以打字告诉我嘛～"
        elif msg_type == "video":
            reply = "视频收到啦～好可惜我暂时看不懂视频呢"
        else:
            reply = "收到啦～但我只看得懂文字消息哦～"

        # 多消息拆分（网页端逐条发送；微信通道受协议限制只能一条）
        parts = split_reply(reply)
        if parts and len(parts) > 1:
            reply = "\n\n".join(parts)

        return PlainTextResponse(_build_xml(user_id, to_user, reply),
                                 media_type="application/xml")

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
    from config import DB_PATH as CHAT_DB

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

    uptime = time.time() - _stats["start_time"]

    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
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
        "reply_cache_size": len(_reply_cache)
    }


@app.on_event("startup")
async def startup():
    logger.info("Starting WeChat AI Companion Server...")
    # 注册本地测试界面（浏览器直接聊，不走微信）
    from test_chat import register_test_routes
    register_test_routes(app)
    logger.info("Server ready!")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down server...")


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
