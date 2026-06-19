"""测试脚本 - 验证服务是否正常"""
import httpx
import xml.etree.ElementTree as ET
import sys

BASE = "http://127.0.0.1:53065"

def test_verify():
    """测试微信验证接口"""
    r = httpx.get(f"{BASE}/wechat", params={
        "signature": "test",
        "timestamp": "123",
        "nonce": "abc",
        "echostr": "hello_verify"
    })
    assert r.status_code == 200
    print("[PASS] 验证接口正常")

def test_message():
    """测试消息收发"""
    xml_data = '''<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[test_user]]></FromUserName>
<CreateTime>1234567890</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[你好]]></Content>
<MsgId>123456</MsgId>
</xml>'''
    r = httpx.post(f"{BASE}/wechat", content=xml_data,
                   headers={"Content-Type": "application/xml"})
    assert r.status_code == 200
    root = ET.fromstring(r.text)
    assert root.find("Content") is not None
    print("[PASS] 消息收发正常")

def test_memory():
    """测试记忆系统"""
    # 发送用户信息
    for msg in ["我叫小红", "我喜欢吃火锅"]:
        xml_data = f'''<xml>
<ToUserName><![CDATA[gh_test]]></ToUserName>
<FromUserName><![CDATA[memory_user]]></FromUserName>
<CreateTime>1234567890</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{msg}]]></Content>
<MsgId>123456</MsgId>
</xml>'''
        httpx.post(f"{BASE}/wechat", content=xml_data,
                   headers={"Content-Type": "application/xml"})

    # 验证数据库
    import sqlite3
    conn = sqlite3.connect("D:/ai项目/wechat-ai/chat.db")
    count = conn.execute("SELECT COUNT(*) FROM chat WHERE user_id='memory_user'").fetchone()[0]
    conn.close()
    assert count >= 4, f"Expected >= 4 messages, got {count}"
    print(f"[PASS] 记忆系统正常 (共 {count} 条记录)")

if __name__ == "__main__":
    try:
        test_verify()
        test_message()
        test_memory()
        print("\n=== 全部测试通过 ===")
    except Exception as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)
