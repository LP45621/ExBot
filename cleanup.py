"""清理过期对话数据"""
import sqlite3
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = "chat.db"

def cleanup_stale_dialogs(days_threshold=7):
    """清理超过N天没有新消息的对话
    
    Args:
        days_threshold: 天数阈值，超过这个天数没有新消息的对话会被清理
    """
    conn = sqlite3.connect(DB_PATH)
    now = time.time()
    threshold = now - (days_threshold * 86400)
    
    # 获取所有对话的最后活跃时间
    rows = conn.execute('''
        SELECT user_id, COUNT(*) as cnt, MAX(time) as last_time 
        FROM chat GROUP BY user_id 
        ORDER BY last_time DESC
    ''').fetchall()
    
    stale = []  # 超过阈值的对话
    active = []  # 活跃对话
    
    for uid, cnt, last_time in rows:
        if last_time < threshold:
            stale.append((uid, cnt, last_time))
        else:
            active.append((uid, cnt, last_time))
    
    print(f"=== Dialog Cleanup (>{days_threshold} days stale) ===")
    print(f"Total dialogs: {len(rows)}")
    print(f"Active (kept): {len(active)}")
    print(f"Stale (to delete): {len(stale)}")
    print()
    
    if not stale:
        print("No stale dialogs to clean up.")
        conn.close()
        return
    
    # 删除过期对话的所有消息
    total_deleted = 0
    for uid, cnt, last_time in stale:
        days_ago = int((now - last_time) / 86400)
        conn.execute("DELETE FROM chat WHERE user_id = ?", (uid,))
        total_deleted += cnt
        print(f"  Deleted: {uid[:30]}... ({cnt} msgs, last active {days_ago}d ago)")
    
    conn.commit()
    
    # 验证结果
    remaining = conn.execute("SELECT COUNT(*) FROM chat").fetchone()[0]
    remaining_dialogs = conn.execute("SELECT COUNT(DISTINCT user_id) FROM chat").fetchone()[0]
    
    print()
    print(f"=== Summary ===")
    print(f"Deleted: {total_deleted} messages from {len(stale)} dialogs")
    print(f"Remaining: {remaining} messages, {remaining_dialogs} dialogs")
    
    conn.close()

def show_dialog_stats():
    """显示对话统计信息"""
    conn = sqlite3.connect(DB_PATH)
    now = time.time()
    
    rows = conn.execute('''
        SELECT user_id, COUNT(*) as cnt, MAX(time) as last_time 
        FROM chat GROUP BY user_id 
        ORDER BY last_time DESC
    ''').fetchall()
    
    print(f"=== Dialog Stats ({len(rows)} dialogs) ===")
    for uid, cnt, last_time in rows[:10]:
        hours_ago = int((now - last_time) / 3600)
        if hours_ago < 24:
            time_str = f"{hours_ago}h ago"
        else:
            days_ago = int(hours_ago / 24)
            time_str = f"{days_ago}d ago"
        print(f"  {uid[:35]}... : {cnt:3d} msgs, {time_str}")
    
    if len(rows) > 10:
        print(f"  ... and {len(rows) - 10} more")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        show_dialog_stats()
    elif len(sys.argv) > 1 and sys.argv[1] == "--clean":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        cleanup_stale_dialogs(days)
    else:
        print("Usage:")
        print("  python cleanup.py --stats      # Show dialog statistics")
        print("  python cleanup.py --clean [N]   # Clean dialogs stale > N days (default 7)")
