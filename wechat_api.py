"""微信客服消息 API —— 超时后主动推送回复，突破5秒限制"""
import asyncio
import time
import logging
import httpx

from config import WECHAT_APPID, WECHAT_APPSECRET

logger = logging.getLogger("wechat")

# access_token 缓存
_token_cache = None
_token_expires_at = 0

# 客服消息 API 地址
CUSTOM_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"


async def get_access_token() -> str:
    """获取微信 access_token（带缓存）"""
    global _token_cache, _token_expires_at

    if _token_cache and time.time() < _token_expires_at - 120:
        return _token_cache

    url = (
        f"https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential"
        f"&appid={WECHAT_APPID}"
        f"&secret={WECHAT_APPSECRET}"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()

        if "access_token" in data:
            _token_cache = data["access_token"]
            _token_expires_at = time.time() + data.get("expires_in", 7200)
            logger.info(f"Access token obtained, expires in {data.get('expires_in')}s")
            return _token_cache
        else:
            logger.error(f"Failed to get access_token: {data}")
            return ""
    except Exception as e:
        logger.error(f"Error getting access_token: {e}")
        return ""


async def send_custom_message(openid: str, content: str) -> bool:
    """通过客服消息接口主动推送消息给用户"""
    token = await get_access_token()
    if not token:
        logger.error("No access_token, cannot send custom message")
        return False

    payload = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": content}
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                CUSTOM_SEND_URL.format(token=token),
                json=payload
            )
            result = resp.json()
            errcode = result.get("errcode", -1)

            if errcode == 0:
                logger.info(f"Custom message sent to {openid[:8]}...: {content[:30]}...")
                return True
            elif errcode == 45015:
                logger.warning(f"User {openid[:8]}... not active in 48h, cannot send")
            elif errcode == 40001:
                _token_cache = None  # 强制刷新 token
                logger.warning("Token invalid, will refresh")
            else:
                logger.error(f"Custom message failed: {result}")

            return False
    except Exception as e:
        logger.error(f"Error sending custom message: {e}")
        return False


async def send_custom_reply(openid: str, msg_id: str, reply: str):
    """后台发送客服回复（在 passive reply 超时后使用）"""
    logger.info(f"Sending custom reply to {openid[:8]}... for MsgId {msg_id[:8]}...")
    success = await send_custom_message(openid, reply)
    if success:
        logger.info(f"Custom reply delivered: {reply[:30]}...")
    else:
        logger.error(f"Custom reply FAILED for {openid[:8]}...")
    return success
