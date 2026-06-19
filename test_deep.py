"""深度优化测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_mood_engine():
    """测试情绪引擎"""
    from mood import MoodEngine, EmotionDetector

    # 测试情绪检测
    detector = EmotionDetector()
    assert detector.detect("我好难过") == "sad"
    assert detector.detect("好开心") == "happy"
    assert detector.detect("喜欢你") == "love"
    assert detector.detect("好累") == "tired"
    assert detector.detect("气死了") == "angry"
    assert detector.detect("好无聊") == "bored"
    assert detector.detect("你好呀") == "neutral"

    # 测试AI心情
    engine = MoodEngine()
    old_mood = engine.mood
    engine.update("happy")
    assert engine.mood != old_mood

    # 测试心情prompt
    prompt = engine.to_prompt()
    assert len(prompt) > 0

    print("[PASS] mood_engine")

def test_human_memory():
    """测试人类化记忆"""
    from human_memory import HumanLikeMemory
    import tempfile

    db_path = os.path.join(tempfile.gettempdir(), "test_human_memory.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    memory = HumanLikeMemory(db_path)

    # 测试存储
    mid = memory.store("test_user", "用户喜欢火锅", "preferences", importance=6)
    assert mid > 0

    mid2 = memory.store("test_user", "下周一面试", "events", importance=9)
    assert mid2 > 0

    # 测试召回
    results = memory.recall("test_user", "火锅")
    assert len(results) > 0
    assert results[0]["content"] == "用户喜欢火锅"

    # 测试画像
    profile = memory.get_profile("test_user")
    assert "用户喜欢火锅" in profile["preferences"]

    # 测试统计
    stats = memory.get_stats("test_user")
    assert stats["total_memories"] == 2

    os.remove(db_path)
    print("[PASS] human_memory")

def test_engine():
    """测试引擎模块"""
    from engine import (
        detect_emotion, detect_intent, should_use_llm,
        route_model, build_messages, split_reply,
        _mood_engine, extract_memory_from_conversation
    )

    # 测试情绪检测
    assert detect_emotion("我好难过") == "sad"
    assert detect_emotion("好开心") == "happy"

    # 测试意图检测
    assert detect_intent("你好") == "hello"
    assert detect_intent("早安") == "morning"
    assert detect_intent("晚安") == "goodbye"
    assert detect_intent("吃什么") == "food"
    assert detect_intent("今天天气真好") == "weather"

    # 测试是否需要LLM
    assert should_use_llm("你好呀", "neutral") == False
    assert should_use_llm("我好难过啊怎么办", "sad") == True
    assert should_use_llm("喜欢你", "love") == True

    # 测试模型路由
    assert route_model("早", "neutral", 100) == "template"
    assert route_model("吃什么", "neutral", 100) == "cheap"
    assert route_model("我好难过", "sad", 100) == "premium"

    # 测试拆句
    segs = split_reply("你好呀～今天天气不错呢。我刚刚吃完饭，你吃了吗？")
    assert len(segs) >= 2

    # 测试build_messages
    messages = build_messages("你好", [], {"user_id": "test"}, "neutral")
    assert len(messages) >= 2
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "你好"

    print("[PASS] engine")

def test_token_optimizer():
    """测试token优化"""
    from token_optimizer import compress_history, compress_message

    # 测试单条压缩
    msg = "我今天去了一个非常非常非常好看的地方，那里有很多很多漂亮的花，我觉得特别特别开心"
    compressed = compress_message(msg, "light")
    assert len(compressed) <= len(msg)

    # 测试历史压缩
    history = [("user", f"这是第{i}条消息，内容比较长一些用来测试压缩效果") for i in range(50)]
    compressed = compress_history(history)
    assert len(compressed) > 0
    assert len(compressed) <= len(history)

    print("[PASS] token_optimizer")

def test_ai_integration():
    """测试AI集成"""
    import asyncio
    from ai import get_ai_reply

    async def run():
        reply = await get_ai_reply("test_integration_user", "你好呀", "test_001")
        assert reply and len(reply) > 0
        return True

    result = asyncio.run(run())
    assert result

    # 清理
    from auto_memory import _get_memory_path
    path = _get_memory_path("test_integration_user")
    if os.path.exists(path):
        os.remove(path)

    print("[PASS] ai_integration")

if __name__ == "__main__":
    print("=" * 50)
    print("  深度优化测试")
    print("=" * 50)
    print()

    tests = [
        test_mood_engine,
        test_human_memory,
        test_engine,
        test_token_optimizer,
        test_ai_integration,
    ]

    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")

    print()
    print(f"结果: {passed}/{len(tests)} 通过")
