"""ExBot 本地测试界面 —— 浏览器直接聊，不走微信"""
from fastapi import Request
from fastapi.responses import HTMLResponse
from engine import _mood_engine

TEST_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ExBot 本地测试</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #ededed; height:100vh; display:flex; flex-direction:column; }
.header { background: #07c160; color:#fff; padding:12px 16px; text-align:center; font-size:16px; font-weight:bold; }
.chat { flex:1; overflow-y:auto; padding:12px; display:flex; flex-direction:column; gap:8px; }
.msg { max-width:80%; padding:10px 14px; border-radius:8px; font-size:15px; line-height:1.5; word-break:break-word; }
.user { align-self:flex-end; background:#95ec69; }
.bot { align-self:flex-start; background:#fff; }
.input-area { display:flex; padding:10px; background:#f5f5f5; gap:8px; border-top:1px solid #ddd; }
.input-area input { flex:1; padding:10px 12px; border:1px solid #ddd; border-radius:20px; font-size:15px; outline:none; }
.input-area button { padding:10px 20px; border:none; border-radius:20px; background:#07c160; color:#fff; font-size:15px; cursor:pointer; }
.info { font-size:12px; color:#999; text-align:center; padding:4px; }
.typing { color:#999; font-style:italic; padding-left:10px; font-size:13px; }
</style>
</head>
<body>
<div class="header">ExBot 小萌 · 本地测试</div>
<div class="chat" id="chat">
    <div class="msg bot">你好呀～我是小萌，直接在下面输入消息跟我聊天吧！</div>
</div>
<div id="typing" style="display:none" class="typing">小萌正在输入...</div>
<div class="input-area">
    <input id="input" type="text" placeholder="输入消息..." autofocus>
    <button onclick="send()">发送</button>
</div>
<div class="info" id="mood">心情: 加载中...</div>

<script>
async function send() {
    const input = document.getElementById('input');
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    input.focus();

    append('user', msg);
    document.getElementById('typing').style.display = 'block';

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: msg})
        });
        const data = await resp.json();
        document.getElementById('typing').style.display = 'none';
        
        // reply 现在是数组，逐条发送模拟真人打字
        const parts = Array.isArray(data.reply) ? data.reply : [data.reply];
        for (let i = 0; i < parts.length; i++) {
            // 打字中闪烁
            const dots = document.getElementById('typing');
            dots.style.display = 'block';
            dots.textContent = '正在输入' + '.'.repeat(i % 3 + 1);
            
            // 模拟打字延迟
            await new Promise(r => setTimeout(r, 500 + Math.random() * 1000));
            
            dots.style.display = 'none';
            append('bot', parts[i].trim());
            document.getElementById('mood').textContent = '心情: ' + data.mood;
            
            // 消息间停顿
            if (i < parts.length - 1) {
                await new Promise(r => setTimeout(r, 800 + Math.random() * 1500));
            }
        }
    } catch (e) {
        document.getElementById('typing').style.display = 'none';
        append('bot', '出错了: ' + e.message);
    }
}

function append(role, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.textContent = text;
    document.getElementById('chat').appendChild(div);
    document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
}

document.getElementById('input').addEventListener('keydown', e => {
    if (e.key === 'Enter') send();
});

fetch('/api/mood').then(r => r.json()).then(d => {
    document.getElementById('mood').textContent = '心情: ' + d.mood;
});
</script>
</body>
</html>"""


def register_test_routes(app):
    """向现有 FastAPI app 注册测试路由"""

    @app.get("/test")
    async def test_page():
        return HTMLResponse(content=TEST_HTML)

    @app.get("/api/mood")
    async def api_mood():
        return {
            "mood": _mood_engine.to_prompt(),
            "emoji": _mood_engine.get_mood_emoji(),
            "value": round(_mood_engine.mood, 2)
        }

    @app.post("/api/chat")
    async def api_chat(request: Request):
        from ai import get_ai_reply
        from engine import split_reply
        body = await request.json()
        msg = body.get("message", "").strip()
        if not msg:
            return {"reply": ["你怎么不说话呀～"], "mood": _mood_engine.get_mood_emoji()}

        try:
            reply = await get_ai_reply("local_test", msg, deadline=15.0)
        except Exception as e:
            reply = f"出错了: {e}"

        # 硬过滤动作描述
        import re as _re
        reply = _re.sub(r'[（(][^）)]*[）)]', '', reply)
        reply = _re.sub(r'[\[【][^\]】]*[\]】]', '', reply)
        reply = reply.strip() or "嗯"

        # 拆成多条短消息
        parts = split_reply(reply)
        if not parts or len(parts) == 1:
            parts = [reply] if reply else ["嗯"]

        return {
            "reply": parts,  # 数组！
            "mood": _mood_engine.get_mood_emoji(),
            "mood_value": round(_mood_engine.mood, 2)
        }
