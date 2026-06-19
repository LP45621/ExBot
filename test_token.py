"""Token 优化 + 记忆系统 测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_token_optimizer():
    """测试 token 压缩"""
    from token_optimizer import compress_message, compress_history, estimate_tokens

    # 测试单条压缩
    msg = "我今天去了一个非常非常非常好看的地方，那里有很多很多漂亮的花，我觉得特别特别开心"
    compressed = compress_message(msg, "light")
    assert len(compressed) <= len(msg), f"Compression failed: {len(compressed)} > {len(msg)}"

    # 测试历史压缩
    history = [("user", f"这是第{i}条消息，内容比较长一些用来测试压缩效果") for i in range(50)]
    compressed = compress_history(history)
    assert len(compressed) > 0
    assert len(compressed) <= len(history)

    # 测试 token 估算
    tokens = estimate_tokens("你好世界")
    assert tokens > 0

    print("[PASS] token_optimizer")

def test_auto_memory():
    """测试自动记忆"""
    from auto_memory import (
        load_user_memory, save_user_memory,
        update_memory_from_conversation, get_memory_context,
        _get_memory_path
    )

    test_uid = "test_memory_user_001"

    # 清理旧数据
    path = _get_memory_path(test_uid)
    if os.path.exists(path):
        os.remove(path)

    # 测试加载空记忆
    memory = load_user_memory(test_uid)
    assert memory["user_id"] == test_uid
    assert memory["total_messages"] == 0

    # 测试更新记忆
    update_memory_from_conversation(test_uid, "我叫小明", "")
    update_memory_from_conversation(test_uid, "我喜欢吃火锅", "")
    update_memory_from_conversation(test_uid, "今天工作好累", "")

    # 测试加载更新后的记忆
    memory = load_user_memory(test_uid)
    
    # 使用字节比较避免编码问题
    name_bytes = memory["name"].encode("utf-8")
    expected_name_bytes = "小明".encode("utf-8")
    assert name_bytes == expected_name_bytes, f"Name bytes mismatch"
    
    prefs_bytes = [p.encode("utf-8") for p in memory["preferences"]]
    expected_pref_bytes = "吃火锅".encode("utf-8")
    assert expected_pref_bytes in prefs_bytes, f"Prefs bytes mismatch: {memory['preferences']}"
    
    assert memory["total_messages"] == 3

    # 测试记忆上下文
    context = get_memory_context(test_uid)
    context_bytes = context.encode("utf-8")
    assert "小明".encode("utf-8") in context_bytes
    assert "吃火锅".encode("utf-8") in context_bytes

    # 清理
    os.remove(_get_memory_path(test_uid))

    print("[PASS] auto_memory")

def test_ai_integration():
    """测试 AI 集成"""
    from ai import sanitize_input, detect_emotion, detect_intent, get_smart_reply, build_messages

    # 测试 build_messages
    messages = build_messages("test_user", "你好呀")
    assert len(messages) >= 2  # system + user
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "你好呀"

    # 测试所有情绪检测
    for text, expected in [("我好难过", "sad"), ("好开心", "happy"), ("好累", "tired"), ("喜欢你", "love"), ("气死了", "angry")]:
        assert detect_emotion(text) == expected

    # 测试所有意图检测
    for text, expected in [("你好", "hello"), ("你叫什么", "self_intro"), ("早安", "morning"), ("晚安", "goodbye")]:
        assert detect_intent(text) == expected

    # 测试 get_smart_reply
    for msg in ["你好", "早安", "晚安", "我好难过", "喜欢你"]:
        reply = get_smart_reply(msg)
        assert reply and len(reply) > 0

    print("[PASS] ai_integration")

def test_full_flow():
    """测试完整流程"""
    import asyncio
    from ai import get_ai_reply

    async def run():
        reply = await get_ai_reply("test_full_flow_user", "你好呀", "test_001")
        assert reply and len(reply) > 0
        return True

    result = asyncio.run(run())
    assert result

    # 清理测试数据
    from auto_memory import _get_memory_path
    path = _get_memory_path("test_full_flow_user")
    if os.path.exists(path):
        os.remove(path)

    print("[PASS] full_flow")

if __name__ == "__main__":
    print("=" * 50)
    print("  Token 优化 + 记忆系统 测试")
    print("=" * 50)
    print()

    tests = [test_token_optimizer, test_auto_memory, test_ai_integration, test_full_flow]

    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")

    print()
    print(f"结果: {passed}/{len(tests)} 通过")
