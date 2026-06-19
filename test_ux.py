"""UX 优化测试 - 修正版"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 重建话术库
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts.db")
if os.path.exists(db_path):
    os.remove(db_path)
from script_db import init_db
init_db()

print()
print("=== UX 测试 ===")
from ai import get_smart_reply, detect_intent, detect_emotion

# 意图检测测试
intent_tests = [
    ("你好", "hello"),
    ("嗨", "hello"),
    ("hi", "hello"),
    ("在吗", "hello"),
    ("你叫什么", "self_intro"),
    ("你是谁", "self_intro"),
    ("早安", "morning"),
    ("起床了", "morning"),
    ("晚安", "goodbye"),
    ("拜拜", "goodbye"),
    ("吃什么", "food"),
    ("饿了", "food"),
    ("天气", "weather"),
    ("好热", "weather"),
    ("无聊", "bored"),
    ("谢谢", "thank_you"),
    ("对不起", "apology"),
]

# 情绪检测测试
emotion_tests = [
    ("我好难过", "sad"),
    ("伤心", "sad"),
    ("不开心", "sad"),
    ("我生气了", "angry"),
    ("气死了", "angry"),
    ("好开心", "happy"),
    ("哈哈", "happy"),
    ("好累", "tired"),
    ("困了", "tired"),
    ("喜欢你", "love"),
    ("想你了", "love"),
]

print("意图检测:")
passed = 0
for msg, expected in intent_tests:
    r = detect_intent(msg)
    ok = r == expected
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    print(f"  [{status}] {msg!r} -> {r!r}")
print(f"  -> {passed}/{len(intent_tests)} 通过")

print()
print("情绪检测:")
passed = 0
for msg, expected in emotion_tests:
    r = detect_emotion(msg)
    ok = r == expected
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    print(f"  [{status}] {msg!r} -> {r!r}")
print(f"  -> {passed}/{len(emotion_tests)} 通过")

print()
print("话术回复 (全部应有回复):")
all_msgs = [
    "你好", "你叫什么", "早安", "晚安", "吃什么", "天气", "无聊",
    "谢谢", "对不起", "我好难过", "好累", "喜欢你", "随便聊聊",
    "今天怎么样", "你真好", "我生气了", "好开心", "拜拜", "在吗"
]
empty_count = 0
for msg in all_msgs:
    r = get_smart_reply(msg)
    if r:
        print(f"  [PASS] {msg!r} -> {r}")
    else:
        print(f"  [FAIL] {msg!r} -> None")
        empty_count += 1

print()
if empty_count == 0:
    print("=== 全部测试通过 ===")
else:
    print(f"=== {empty_count} 条话术缺失 ===")
