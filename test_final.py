"""全面测试脚本 - 最终版"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """测试配置模块"""
    from config import PORT, WECHAT_TOKEN, DEEPSEEK_API_KEY, SYSTEM_PROMPT, DB_PATH
    assert PORT > 0
    assert len(WECHAT_TOKEN) > 0
    assert len(DEEPSEEK_API_KEY) > 0
    assert len(SYSTEM_PROMPT) > 100
    assert DB_PATH.endswith("chat.db")
    print("[PASS] config")

def test_memory():
    """测试记忆模块"""
    from memory import save_message, get_history, get_message_count, get_user_summary, get_user_info
    test_uid = "test_memory_user"

    save_message(test_uid, "user", "test message 1")
    save_message(test_uid, "assistant", "test reply 1")
    save_message(test_uid, "user", "test message 2")

    history = get_history(test_uid)
    assert len(history) >= 3

    count = get_message_count(test_uid)
    assert count >= 3

    info = get_user_info(test_uid)
    assert "last_chat" in info

    print("[PASS] memory")

def test_script_db():
    """测试话术库"""
    from script_db import get_random, init_db

    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    init_db()

    for cat in ["hello", "self_intro", "greetings", "emotional_responses", "small_talk", "flirty", "caring", "jokes", "riddles", "unknown"]:
        result = get_random(cat)
        assert result is not None, f"get_random({cat}) returned None"

    print("[PASS] script_db")

def test_ai():
    """测试AI模块"""
    from ai import detect_emotion, detect_intent, sanitize_input, get_smart_reply

    assert detect_emotion("我好难过") == "sad"
    assert detect_emotion("好开心呀") == "happy"
    assert detect_emotion("好累") == "tired"
    assert detect_emotion("你好呀") is None
    assert detect_emotion("喜欢你") == "love"
    assert detect_emotion("气死了") == "angry"

    assert detect_intent("你好") == "hello"
    assert detect_intent("你叫什么") == "self_intro"
    assert detect_intent("早安") == "morning"
    assert detect_intent("晚安") == "goodbye"
    assert detect_intent("吃什么") == "food"
    assert detect_intent("天气") == "weather"
    assert detect_intent("无聊") == "bored"
    assert detect_intent("谢谢") == "thank_you"
    assert detect_intent("对不起") == "apology"
    assert detect_intent("今天天气真好") == "weather"
    assert detect_intent("我在学Python") is None

    assert sanitize_input("  hello  ") == "hello"
    assert sanitize_input("a" * 600)[:500] == "a" * 500
    assert sanitize_input("") == ""
    assert sanitize_input(None) == ""

    for msg in ["你好", "你叫什么", "早安", "晚安", "吃什么", "天气", "无聊", "谢谢", "对不起", "我好难过", "好累", "喜欢你"]:
        reply = get_smart_reply(msg)
        assert reply is not None and len(reply) > 0, f"get_smart_reply({msg!r}) failed"

    print("[PASS] ai")

def test_api_call():
    """测试API调用"""
    import httpx
    from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL

    r = httpx.post(DEEPSEEK_API_URL,
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json={"model": DEEPSEEK_MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10},
        timeout=10
    )
    assert r.status_code == 200
    print("[PASS] api_call")

def test_signature():
    """测试签名验证"""
    from main import verify_signature
    import hashlib

    token = "test_token"
    ts = "1234567890"
    nonce = "abc"
    items = sorted([token, ts, nonce])
    sig = hashlib.sha1("".join(items).encode()).hexdigest()

    assert verify_signature(token, sig, ts, nonce) == True
    assert verify_signature(token, "wrong", ts, nonce) == False
    assert verify_signature("", sig, ts, nonce) == False

    print("[PASS] signature")

def test_rate_limit():
    """测试速率限制"""
    from main import check_rate_limit, _rate_limit

    _rate_limit.clear()
    uid = "test_rl_user"

    for i in range(10):
        assert check_rate_limit(uid) == True

    assert check_rate_limit(uid) == False

    _rate_limit.clear()
    print("[PASS] rate_limit")

def test_duplicate_check():
    """测试消息去重"""
    from main import check_wechat_duplicate

    rid = "test_dup"
    body1 = b"test body"
    body2 = b"test body"
    body3 = b"different body"

    assert check_wechat_duplicate(rid, body1) == False
    assert check_wechat_duplicate(rid, body2) == True
    assert check_wechat_duplicate(rid, body3) == False

    print("[PASS] duplicate_check")

def test_server():
    """测试HTTP服务"""
    import httpx
    import xml.etree.ElementTree as ET

    r = httpx.get("http://127.0.0.1:53065/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")

    xml_data = '''<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[test_user]]></FromUserName>
<CreateTime>1234567890</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[你好]]></Content>
<MsgId>123456</MsgId>
</xml>'''
    r = httpx.post("http://127.0.0.1:53065/wechat", content=xml_data,
                   headers={"Content-Type": "application/xml"}, timeout=10)
    assert r.status_code == 200
    root = ET.fromstring(r.text)
    assert root.find("Content") is not None

    print("[PASS] server")

if __name__ == "__main__":
    print("=" * 50)
    print("  全面测试 - 最终版")
    print("=" * 50)
    print()

    tests = [
        test_config,
        test_memory,
        test_script_db,
        test_ai,
        test_signature,
        test_rate_limit,
        test_duplicate_check,
        test_api_call,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1

    print()
    print(f"结果: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n启动服务器进行集成测试...")
        import subprocess
        import time
        proc = subprocess.Popen([sys.executable, "main.py"],
                                cwd=os.path.dirname(os.path.abspath(__file__)),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        try:
            test_server()
            print("\n=== 全部测试通过 ===")
        except Exception as e:
            print(f"\n[FAIL] server: {e}")
        finally:
            proc.terminate()
            proc.wait()
