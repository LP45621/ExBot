"""网页测试界面 —— 浏览器直接聊，不走微信，带侧边调试面板"""
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ai import get_ai_reply
from engine import split_reply, _mood_engine, get_memory_system


def register_test_routes(app: FastAPI):
    """注册测试路由"""

    @app.get("/test", response_class=HTMLResponse)
    async def test_page():
        return """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Chat Test</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f5f5f5;height:100vh;display:flex}
#sidebar{width:300px;background:#1a1a2e;color:#eee;padding:16px;overflow-y:auto;font-size:13px;flex-shrink:0}
#sidebar h3{color:#00d4ff;margin:12px 0 8px;font-size:14px;border-bottom:1px solid #333;padding-bottom:4px}
#sidebar .stat{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #222}
#sidebar .stat .label{color:#888}
#sidebar .stat .value{color:#fff;font-weight:500}
#sidebar .desc{color:#666;font-size:11px;padding:2px 0 6px;line-height:1.4}
#sidebar .mood-bar{height:8px;background:#333;border-radius:4px;margin:8px 0;overflow:hidden}
#sidebar .mood-fill{height:100%;border-radius:4px;transition:width 0.5s}
#sidebar .memory-item{padding:6px 0;border-bottom:1px solid #222;font-size:12px;color:#aaa}
#sidebar .memory-item .type{color:#00d4ff;font-size:11px}
#main{flex:1;display:flex;flex-direction:column}
#chat{flex:1;overflow-y:auto;padding:16px;max-width:600px;margin:0 auto;width:100%}
.msg{margin:8px 0;display:flex}
.msg.user{justify-content:flex-end}
.msg.ai{justify-content:start}
.bubble{max-width:75%;padding:10px 14px;border-radius:16px;font-size:14px;line-height:1.5;word-break:break-word}
.msg.user .bubble{background:#95ec69;color:#000;border-bottom-right-radius:4px}
.msg.ai .bubble{background:#fff;color:#000;border-bottom-left-radius:4px;box-shadow:0 1px 2px rgba(0,0,0,.1)}
#input-area{display:flex;gap:8px;padding:12px 16px;background:#fff;border-top:1px solid #e5e5e5;max-width:600px;margin:0 auto;width:100%}
#input{flex:1;border:1px solid #ddd;border-radius:20px;padding:8px 16px;font-size:14px;outline:none}
#send{background:#07c160;color:#fff;border:none;border-radius:20px;padding:8px 20px;font-size:14px;cursor:pointer}
.typing{color:#999;font-size:12px;padding:4px 14px;display:none}
</style>
</head><body>
<div id="sidebar">
<h3>🤖 AI 状态</h3>
<div class="stat"><span class="label">心情</span><span class="value" id="mood-text">-</span></div>
<div class="desc">AI当前情绪描述，由对话内容动态更新</div>
<div class="mood-bar"><div class="mood-fill" id="mood-bar" style="width:50%;background:#00d4ff"></div></div>
<div class="stat"><span class="label">心情值</span><span class="value" id="mood-value">0.50</span></div>
<div class="desc">0=低落, 0.5=平静, 1=兴奋，影响回复语气</div>
<div class="stat"><span class="label">心情表情</span><span class="value" id="mood-emoji">🙂</span></div>
<div class="desc">心情值对应的emoji表情</div>
<div class="stat"><span class="label">闹脾气</span><span class="value" id="mood-sulk">否</span></div>
<div class="desc">连续收到负面消息时触发，回复会变冷淡</div>
<div class="stat"><span class="label">兴奋</span><span class="value" id="mood-excited">否</span></div>
<div class="desc">收到正面消息时触发，回复会更热情</div>

<h3>📊 统计</h3>
<div class="stat"><span class="label">总请求</span><span class="value" id="stat-requests">0</span></div>
<div class="desc">收到的微信/HTTP请求总数</div>
<div class="stat"><span class="label">总消息</span><span class="value" id="stat-messages">0</span></div>
<div class="desc">成功处理的用户消息数</div>
<div class="stat"><span class="label">总错误</span><span class="value" id="stat-errors">0</span></div>
<div class="desc">处理失败的次数（API超时、解析错误等）</div>
<div class="stat"><span class="label">运行时间</span><span class="value" id="stat-uptime">0s</span></div>
<div class="desc">服务启动至今的时长</div>

<h3>💾 记忆</h3>
<div class="desc">AI记住的关于你的事情（遗忘曲线衰减）</div>
<div id="memory-list">加载中...</div>

<h3>👤 用户</h3>
<div class="stat"><span class="label">用户ID</span><span class="value" id="user-id">-</span></div>
<div class="desc">唯一标识，微信=OpenID，网页=随机生成</div>
<div class="stat"><span class="label">消息数</span><span class="value" id="user-msgs">0</span></div>
<div class="desc">你和AI总共聊了多少条消息</div>
</div>

<div id="main">
<div id="chat"></div>
<div id="input-area">
<input id="input" placeholder="说点什么..." autocomplete="off">
<button id="send">发送</button>
</div>
</div>

<script>
const chat=document.getElementById('chat'),input=document.getElementById('input');
const uid='web-'+Date.now();
document.getElementById('user-id').textContent=uid.substring(0,16)+'...';

function addMsg(text,who){
    const div=document.createElement('div');div.className='msg '+who;
    const b=document.createElement('div');b.className='bubble';b.textContent=text;
    div.appendChild(b);chat.appendChild(div);chat.scrollTop=chat.scrollHeight;
}
function addTyping(){const d=document.createElement('div');d.className='typing';d.id='typing';d.textContent='对方正在输入...';chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}
function removeTyping(){const t=document.getElementById('typing');if(t)t.remove();}

async function send(){
    const text=input.value.trim();if(!text)return;input.value='';
    addMsg(text,'user');addTyping();
    try{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,user_id:uid})});
        const d=await r.json();removeTyping();
        if(d.reply){const parts=d.reply.split('\\n\\n');parts.forEach(p=>{if(p.trim())addMsg(p.trim(),'ai')});}
        updateDebug();
    }catch(e){removeTyping();addMsg('发送失败','ai');}
}

async function updateDebug(){
    try{
        const r=await fetch('/api/debug?user_id='+uid);
        const d=await r.json();
        // 心情
        const m=d.mood||{};
        document.getElementById('mood-text').textContent=m.description||'-';
        document.getElementById('mood-value').textContent=(m.current||0).toFixed(2);
        document.getElementById('mood-emoji').textContent=m.emoji||'🙂';
        document.getElementById('mood-sulk').textContent=m.is_sulking?'是':'否';
        document.getElementById('mood-excited').textContent=m.is_excited?'是':'否';
        const bar=document.getElementById('mood-bar');
        bar.style.width=((m.current||0.5)*100)+'%';
        bar.style.background=m.current>0.6?'#00d4ff':m.current>0.3?'#ffaa00':'#ff4444';
        // 统计
        const s=d.stats||{};
        document.getElementById('stat-requests').textContent=s.total_requests||0;
        document.getElementById('stat-messages').textContent=s.total_messages||0;
        document.getElementById('stat-errors').textContent=s.total_errors||0;
        const up=Math.floor(s.uptime||0);
        document.getElementById('stat-uptime').textContent=up>3600?Math.floor(up/3600)+'h':up>60?Math.floor(up/60)+'m':up+'s';
        // 记忆
        const memories=d.memories||[];
        const ml=document.getElementById('memory-list');
        if(memories.length===0){ml.innerHTML='<div class="memory-item">暂无记忆</div>';}
        else{ml.innerHTML=memories.map(m=>'<div class="memory-item"><span class="type">['+m.type+']</span> '+m.content+'</div>').join('');}
        // 用户
        document.getElementById('user-msgs').textContent=d.user_messages||0;
    }catch(e){}
}

document.getElementById('send').onclick=send;
input.onkeydown=e=>{if(e.key==='Enter')send()};
updateDebug();
setInterval(updateDebug,5000);
</script></body></html>"""

    @app.post("/api/chat")
    async def api_chat(body: dict):
        message = body.get("message", "").strip()
        user_id = body.get("user_id", "web_user")
        if not message:
            return {"reply": "你怎么不说话呀～"}

        try:
            reply = await get_ai_reply(user_id, message)
            parts = split_reply(reply)
            if parts and len(parts) > 1:
                reply = "\n\n".join(parts)
            return {"reply": reply}
        except Exception as e:
            return {"reply": f"出错啦: {str(e)}"}

    @app.get("/api/debug")
    async def api_debug(user_id: str = ""):
        """调试接口：返回AI状态+用户记忆"""
        from memory import get_message_count
        mood = _mood_engine

        memories = []
        if user_id:
            try:
                mem_system = get_memory_system()
                mems = mem_system.recall(user_id, "", top_k=5)
                memories = [{"type": m.get("memory_type", "?"), "content": m.get("content", "")[:50]} for m in mems]
            except Exception:
                pass

        return {
            "mood": {
                "current": round(mood.mood, 2),
                "description": mood.to_prompt(),
                "emoji": mood.get_mood_emoji(),
                "is_sulking": mood.is_sulking(),
                "is_excited": mood.is_excited(),
            },
            "stats": {
                "total_requests": 0,
                "total_messages": 0,
                "total_errors": 0,
                "uptime": time.time() - mood.mood_history[0] if mood.mood_history else 0,
            },
            "memories": memories,
            "user_messages": get_message_count(user_id) if user_id else 0,
        }
