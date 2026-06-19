"""微信消息队列 - 处理5秒超时"""
import asyncio
import time
import logging
from collections import defaultdict
from typing import Callable, Any

logger = logging.getLogger("wechat")


class MessageQueue:
    """微信消息队列，解决5秒超时问题"""

    def __init__(self, max_size: int = 100):
        self.queue = asyncio.Queue(maxsize=max_size)
        self.processing = False
        self.stats = {
            "total": 0,
            "processed": 0,
            "failed": 0,
            "pending": 0
        }

    async def put(self, user_id: str, content: str, callback: Callable):
        """添加消息到队列"""
        await self.queue.put({
            "user_id": user_id,
            "content": content,
            "callback": callback,
            "time": time.time()
        })
        self.stats["total"] += 1
        self.stats["pending"] = self.queue.qsize()

    async def process(self):
        """处理队列中的消息"""
        if self.processing:
            return
        self.processing = True

        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                self.stats["pending"] = self.queue.qsize()

                try:
                    await item["callback"](item["user_id"], item["content"])
                    self.stats["processed"] += 1
                except Exception as e:
                    logger.error(f"Process message failed: {e}")
                    self.stats["failed"] += 1

            except asyncio.QueueEmpty:
                break

        self.processing = False

    def get_stats(self):
        """获取队列统计"""
        return {
            **self.stats,
            "queue_size": self.queue.qsize()
        }


# 全局消息队列
message_queue = MessageQueue()


async def start_queue_processor():
    """启动队列处理器"""
    while True:
        await message_queue.process()
        await asyncio.sleep(0.1)


# 后台任务
_queue_task = None

def ensure_queue_running():
    """确保队列处理器在运行"""
    global _queue_task
    if _queue_task is None or _queue_task.done():
        _queue_task = asyncio.create_task(start_queue_processor())
