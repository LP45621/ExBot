"""网页测试界面 —— 浏览器直接聊，不走微信，带侧边调试面板+对话切换"""
import time
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ai import get_ai_reply
from engine import split_reply, _mood_engine, get_memory_system


def _is_local_request(request: Request) -> bool:
    client_ip = request.client.host if request.client else ""
    return client_ip in ("127.0.0.1", "::1", "localhost")


def _local_only_response():
    return JSONResponse({"error": "仅限本地访问"}, status_code=403)


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
#sidebar button{background:#00d4ff;color:#1a1a2e;border:none;border-radius:6px;padding:8px 16px;font-size:12px;cursor:pointer;margin:4px 0;width:100%}
#sidebar button:hover{background:#00b8d4}
#sidebar .conv-list{max-height:200px;overflow-y:auto;margin:8px 0}
#sidebar .conv-item{padding:8px;border-radius:6px;cursor:pointer;margin:4px 0;background:#222;font-size:12px}
#sidebar .conv-item:hover{background:#333}
#sidebar .conv-item.active{background:#00d4ff;color:#1a1a2e}
#sidebar .conv-item .conv-time{font-size:10px;color:#888}
#sidebar .conv-item .conv-preview{margin-top:4px;color:#aaa;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#sidebar .conv-item.active .conv-time,#sidebar .conv-item.active .conv-preview{color:#1a1a2e}
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
<h3>💬 对话列表</h3>
<button onclick="newConversation()">➕ 新对话</button>
<div class="conv-list" id="conv-list"></div>

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
<button onclick="backupMemories()">📥 备份记忆</button>
<button onclick="exportChat()">📥 导出聊天记录</button>
<button onclick="clearChat()">🗑️ 清空当前对话</button>
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
let currentConvId=null;

// 对话管理
function getConversations(){return JSON.parse(localStorage.getItem('conversations')||'[]');}
function saveConversations(convs){localStorage.setItem('conversations',JSON.stringify(convs));}
function getConvMessages(convId){return JSON.parse(localStorage.getItem('conv_'+convId)||'[]');}
function saveConvMessages(convId,msgs){localStorage.setItem('conv_'+convId,JSON.stringify(msgs));}

function newConversation(){
    const convs=getConversations();
    const convId='conv_'+Date.now();
    convs.unshift({id:convId,time:Date.now(),preview:'新对话'});
    saveConversations(convs);
    switchConversation(convId);
}

function switchConversation(convId){
    currentConvId=convId;
    chat.innerHTML='';
    const msgs=getConvMessages(convId);
    msgs.forEach(m=>addMsg(m.text,m.who,false,m.time));
    renderConvList();
}

function renderConvList(){
    const convs=getConversations();
    const list=document.getElementById('conv-list');
    list.innerHTML='';
    convs.forEach(c=>{
        const div=document.createElement('div');
        div.className='conv-item'+(c.id===currentConvId?' active':'');
        const d=new Date(c.time);
        div.innerHTML='<div class="conv-time">'+d.toLocaleDateString()+' '+d.toLocaleTimeString()+'</div><div class="conv-preview">'+c.preview+'</div>';
        div.onclick=()=>switchConversation(c.id);
        list.appendChild(div);
    });
}

function updateConvPreview(){
    if(!currentConvId)return;
    const convs=getConversations();
    const msgs=getConvMessages(currentConvId);
    const lastMsg=msgs.length>0?msgs[msgs.length-1].text:'新对话';
    const idx=convs.findIndex(c=>c.id===currentConvId);
    if(idx>=0){convs[idx].preview=lastMsg.substring(0,30);convs[idx].time=Date.now();saveConversations(convs);renderConvList();}
}

// 消息管理
function addMsg(text,who,save=true,timestamp){
    const now=timestamp?new Date(timestamp):new Date();
    const timeStr=now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
    
    const div=document.createElement('div');div.className='msg '+who;
    const b=document.createElement('div');b.className='bubble';b.textContent=text;
    const ts=document.createElement('div');ts.className='timestamp';ts.style.cssText='font-size:11px;color:#999;margin-top:2px;padding:0 14px;'+(who==='user'?'text-align:right':'');
    ts.textContent=timeStr;
    div.appendChild(b);chat.appendChild(div);chat.appendChild(ts);chat.scrollTop=chat.scrollHeight;
    if(save&&currentConvId){
        const msgs=getConvMessages(currentConvId);
        msgs.push({text,who,time:Date.now()});
        saveConvMessages(currentConvId,msgs);
        updateConvPreview();
    }
}
function addTyping(){const d=document.createElement('div');d.className='typing';d.id='typing';d.textContent='对方正在输入...';chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}
function removeTyping(){const t=document.getElementById('typing');if(t)t.remove();}
function addSystemMsg(text){const d=document.createElement('div');d.style.cssText='text-align:center;color:#999;font-size:12px;margin:8px 0;padding:4px 12px;background:#f0f0f0;border-radius:12px;display:inline-block;';d.textContent=text;const w=document.createElement('div');w.style.cssText='display:flex;justify-content:center;';w.appendChild(d);chat.appendChild(w);chat.scrollTop=chat.scrollHeight;}

async function send(){
    const text=input.value.trim();if(!text)return;input.value='';
    if(!currentConvId)newConversation();
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
        const m=d.mood||{};
        document.getElementById('mood-text').textContent=m.description||'-';
        document.getElementById('mood-value').textContent=(m.current||0).toFixed(2);
        document.getElementById('mood-emoji').textContent=m.emoji||'🙂';
        document.getElementById('mood-sulk').textContent=m.is_sulking?'是':'否';
        document.getElementById('mood-excited').textContent=m.is_excited?'是':'否';
        const bar=document.getElementById('mood-bar');
        bar.style.width=((m.current||0.5)*100)+'%';
        bar.style.background=m.current>0.6?'#00d4ff':m.current>0.3?'#ffaa00':'#ff4444';
        const s=d.stats||{};
        document.getElementById('stat-requests').textContent=s.total_requests||0;
        document.getElementById('stat-messages').textContent=s.total_messages||0;
        document.getElementById('stat-errors').textContent=s.total_errors||0;
        const up=Math.floor(s.uptime||0);
        document.getElementById('stat-uptime').textContent=up>3600?Math.floor(up/3600)+'h':up>60?Math.floor(up/60)+'m':up+'s';
        const memories=d.memories||[];
        const ml=document.getElementById('memory-list');
        if(memories.length===0){ml.innerHTML='<div class="memory-item">暂无记忆</div>';}
        else{ml.innerHTML=memories.map(m=>'<div class="memory-item"><span class="type">['+m.type+']</span> '+m.content+'</div>').join('');}
    }catch(e){}
}

async function backupMemories(){
    try{
        const r=await fetch('/api/backup?user_id='+uid);
        const d=await r.json();
        const blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});
        const a=document.createElement('a');a.href=URL.createObjectURL(blob);
        a.download='memory_backup_'+new Date().toISOString().slice(0,10)+'.json';
        a.click();
    }catch(e){alert('备份失败: '+e);}
}

function exportChat(){
    if(!currentConvId){alert('没有对话');return;}
    const msgs=getConvMessages(currentConvId);
    if(msgs.length===0){alert('没有聊天记录');return;}
    const text=msgs.map(m=>(m.who==='user'?'我':'AI')+': '+m.text).join('\\n');
    const blob=new Blob([text],{type:'text/plain'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download='chat_'+new Date().toISOString().slice(0,10)+'.txt';
    a.click();
}

function clearChat(){
    if(!currentConvId)return;
    if(confirm('确定清空当前对话？')){
        localStorage.removeItem('conv_'+currentConvId);
        chat.innerHTML='';
        const convs=getConversations();
        const idx=convs.findIndex(c=>c.id===currentConvId);
        if(idx>=0){convs[idx].preview='新对话';saveConversations(convs);renderConvList();}
    }
}

document.getElementById('send').onclick=send;
input.onkeydown=e=>{if(e.key==='Enter')send()};

// 初始化：加载最近对话或创建新对话
const convs=getConversations();
if(convs.length>0){switchConversation(convs[0].id);}
else{newConversation();}
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
            
            # AI 选择不回复
            if not reply or not reply.strip():
                return {"reply": "", "no_reply": True}
            
            parts = split_reply(reply)
            if parts and len(parts) > 1:
                reply = "\n\n".join(parts)
            return {"reply": reply}
        except Exception as e:
            return {"reply": f"出错啦: {str(e)}"}

    @app.get("/api/debug")
    async def api_debug(request: Request, user_id: str = ""):
        """调试接口：返回AI状态+用户记忆"""
        if not _is_local_request(request):
            return _local_only_response()

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
                "uptime": 0,
            },
            "memories": memories,
            "user_messages": get_message_count(user_id) if user_id else 0,
        }

    @app.get("/api/backup")
    async def api_backup(request: Request, user_id: str = ""):
        """记忆备份接口：导出用户所有记忆"""
        if not _is_local_request(request):
            return _local_only_response()

        from memory import get_history, get_user_info
        from auto_memory import load_user_memory

        if not user_id:
            return JSONResponse({"error": "需要user_id"}, status_code=400)

        try:
            history = get_history(user_id, limit=1000)
            user_info = get_user_info(user_id)
            auto_mem = load_user_memory(user_id)
            mem_system = get_memory_system()
            long_mem = mem_system.recall(user_id, "", top_k=50)

            return {
                "user_id": user_id,
                "backup_time": time.time(),
                "chat_history": [{"role": r, "content": c} for r, c in history],
                "user_profile": user_info,
                "auto_memory": auto_mem,
                "long_term_memories": [{"type": m.get("memory_type"), "content": m.get("content"), "importance": m.get("importance")} for m in long_mem],
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/api/conversations")
    async def api_conversations(request: Request):
        """获取所有对话列表（从数据库）"""
        if not _is_local_request(request):
            return _local_only_response()

        import sqlite3
        from config import DB_PATH
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            rows = conn.execute(
                "SELECT user_id, COUNT(*) as cnt, MAX(time) as last_time FROM chat GROUP BY user_id ORDER BY last_time DESC"
            ).fetchall()
            conn.close()
            return {
                "conversations": [
                    {"user_id": r[0], "count": r[1], "last_time": r[2]}
                    for r in rows if not r[0].startswith("test")  # 排除测试数据
                ]
            }
        except Exception as e:
            return {"conversations": [], "error": str(e)}

    @app.get("/api/history/{user_id}")
    async def api_history(request: Request, user_id: str, limit: int = 500):
        """获取指定用户的聊天历史（含时间戳）"""
        if not _is_local_request(request):
            return _local_only_response()

        import sqlite3
        from config import DB_PATH
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            if limit > 0:
                rows = conn.execute(
                    "SELECT role, content, time FROM chat WHERE user_id = ? ORDER BY time DESC LIMIT ?",
                    (user_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT role, content, time FROM chat WHERE user_id = ? ORDER BY time DESC",
                    (user_id,)
                ).fetchall()
            conn.close()
            return {
                "user_id": user_id,
                "messages": [{"role": r, "content": c, "time": t} for r, c, t in reversed(rows)]
            }
        except Exception as e:
            return {"user_id": user_id, "messages": [], "error": str(e)}

    @app.get("/api/pending_messages")
    async def api_pending_messages(user_id: str = ""):
        """获取用户未读的主动消息"""
        from memory import get_pending_messages, mark_pending_delivered
        
        if not user_id:
            return {"messages": []}
        
        try:
            pending = get_pending_messages(user_id)
            if pending:
                # 标记为已送达
                msg_ids = [m["id"] for m in pending]
                mark_pending_delivered(msg_ids)
                
                # 格式化返回
                messages = []
                for p in pending:
                    ts = p["created_at"]
                    messages.append({
                        "content": p["content"],
                        "timestamp": ts,
                        "silence_minutes": p["silence_minutes"],
                        "is_proactive": True
                    })
                return {"messages": messages}
            return {"messages": []}
        except Exception as e:
            return {"messages": [], "error": str(e)}

    @app.get("/chat", response_class=HTMLResponse)
    async def chat_page():
        """DeepSeek风格聊天界面"""
        return """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Chat</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f7f7f8;height:100vh;display:flex}
#sidebar{width:260px;background:#1e1e2e;color:#eee;display:flex;flex-direction:column}
#sidebar-header{padding:16px;border-bottom:1px solid #333}
#sidebar-header h2{font-size:16px;color:#fff;margin-bottom:12px}
#new-chat{width:100%;padding:10px;background:#2d2d3e;border:1px solid #444;border-radius:8px;color:#fff;cursor:pointer;font-size:13px}
#new-chat:hover{background:#3d3d4e}
#conv-list{flex:1;overflow-y:auto;padding:8px}
.conv-item{padding:10px 12px;border-radius:8px;cursor:pointer;margin:4px 0;font-size:13px;color:#ccc}
.conv-item:hover{background:#2d2d3e}
.conv-item.active{background:#3d3d4e;color:#fff}
.conv-item .conv-preview{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#main{flex:1;display:flex;flex-direction:column;background:#fff}
#header{padding:12px 20px;border-bottom:1px solid #e5e5e5;display:flex;align-items:center;gap:12px}
#header .model-select{padding:6px 12px;border:1px solid #ddd;border-radius:6px;font-size:13px;background:#fff}
#messages{flex:1;overflow-y:auto;padding:20px;max-width:800px;margin:0 auto;width:100%}
.msg{margin:16px 0;display:flex}
.msg.user{justify-content:flex-end}
.msg.ai{justify-content:start}
.msg .avatar{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.msg.user .avatar{background:#95ec69;color:#000}
.msg.ai .avatar{background:#4a90d9;color:#fff}
.msg .content{max-width:70%;padding:12px 16px;border-radius:12px;font-size:14px;line-height:1.6;word-break:break-word}
.msg.user .content{background:#95ec69;color:#000;border-bottom-right-radius:4px;margin-right:8px}
.msg.ai .content{background:#f0f0f0;color:#000;border-bottom-left-radius:4px;margin-left:8px}
.msg .timestamp{font-size:11px;color:#999;margin-top:4px;padding:0 8px}
.msg.user .timestamp{text-align:right}
.msg.ai .timestamp{text-align:left}
#input-area{padding:16px 20px;border-top:1px solid #e5e5e5;background:#fff}
#input-wrapper{max-width:800px;margin:0 auto;display:flex;gap:12px;align-items:flex-end}
#input{flex:1;border:1px solid #ddd;border-radius:12px;padding:12px 16px;font-size:14px;outline:none;resize:none;min-height:44px;max-height:200px;font-family:inherit}
#input:focus{border-color:#4a90d9}
#send{background:#4a90d9;color:#fff;border:none;border-radius:12px;padding:12px 24px;font-size:14px;cursor:pointer}
#send:hover{background:#3a7bc8}
#send:disabled{background:#ccc;cursor:not-allowed}
.typing{color:#999;font-size:13px;padding:8px 16px;display:none}
.welcome{text-align:center;color:#999;margin-top:40px}
.welcome h2{color:#333;margin-bottom:8px}
</style>
</head><body>
<div id="sidebar">
<div id="sidebar-header">
<h2>💬 AI Chat</h2>
<button id="new-chat" onclick="newConversation()">+ 新对话</button>
</div>
<div id="conv-list"></div>
<div style="padding:12px;border-top:1px solid #333">
<button onclick="exportChat()" style="width:100%;padding:8px;background:#2d2d3e;border:1px solid #444;border-radius:6px;color:#fff;cursor:pointer;font-size:12px">📥 导出聊天记录</button>
</div>
</div>
<div id="main">
<div id="header">
<select class="model-select" id="model-select">
<option value="deepseek-chat">DeepSeek Chat</option>
<option value="deepseek-coder">DeepSeek Coder</option>
</select>
<span style="color:#999;font-size:13px" id="status">就绪</span>
</div>
<div id="messages">
<div class="welcome">
<h2>👋 你好！</h2>
<p>我是AI助手，有什么可以帮你的？</p>
</div>
</div>
<div id="typing" class="typing">AI正在思考...</div>
<div id="input-area">
<div id="input-wrapper">
<textarea id="input" placeholder="输入消息..." rows="1"></textarea>
<button id="send" onclick="send()">发送</button>
</div>
</div>
</div>
<script>
const messages=document.getElementById('messages'),input=document.getElementById('input');
// 保持用户ID持久化（刷新页面不丢失）
function getUserId(){
    let saved=localStorage.getItem('chat_uid');
    if(!saved){saved='chat-'+Date.now();localStorage.setItem('chat_uid',saved);}
    return saved;
}
const uid=getUserId();
let currentConvId=null;
let isTyping=false;

// 对话管理
function getConversations(){return JSON.parse(localStorage.getItem('chat_convs')||'[]');}
function saveConversations(convs){localStorage.setItem('chat_convs',JSON.stringify(convs));}
function getConvMessages(convId){return JSON.parse(localStorage.getItem('chat_msg_'+convId)||'[]');}
function saveConvMessages(convId,msgs){localStorage.setItem('chat_msg_'+convId,JSON.stringify(msgs));}

// 从服务器加载历史对话列表
async function loadFromServer(){
    try{
        const r=await fetch('/api/conversations');
        const d=await r.json();
        if(!d.conversations||d.conversations.length===0)return;
        
        const convs=getConversations();
        const existingIds=new Set(convs.map(c=>c.id));
        
        for(const conv of d.conversations){
            if(existingIds.has(conv.user_id))continue;
            if(conv.user_id.startsWith('test'))continue;
            convs.push({id:conv.user_id,time:conv.last_time*1000,preview:'('+conv.count+'条记录)',fromServer:true});
        }
        
        convs.sort((a,b)=>b.time-a.time);
        saveConversations(convs);
        renderConvList();
    }catch(e){console.log('Load from server failed:',e);}
}

// 从服务器加载指定对话的历史消息
async function loadHistoryFromServer(userId){
    try{
        const r=await fetch('/api/history/'+encodeURIComponent(userId)+'?limit=500');
        const d=await r.json();
        if(!d.messages||d.messages.length===0)return null;
        
        const msgs=d.messages.map((m,i)=>({
            text:m.content,
            who:m.role==='user'?'user':'ai',
            time:m.time>0?m.time*1000:Date.now()-((d.messages.length-i)*60000)
        }));
        saveConvMessages(userId,msgs);
        return msgs;
    }catch(e){console.log('Load history failed:',e);return null;}
}

function newConversation(){
    const convs=getConversations();
    const convId='conv_'+Date.now();
    convs.unshift({id:convId,time:Date.now(),preview:'新对话'});
    saveConversations(convs);
    switchConversation(convId);
}

async function switchConversation(convId){
    currentConvId=convId;
    messages.innerHTML='';
    lastMsgTime=0; // 重置时间显示
    
    let msgs=getConvMessages(convId);
    
    // 如果本地没有消息，尝试从服务器加载
    if(msgs.length===0){
        const loaded=await loadHistoryFromServer(convId);
        if(loaded)msgs=loaded;
    }
    
    if(msgs.length===0){
        messages.innerHTML='<div class="welcome"><h2>👋 你好！</h2><p>我是AI助手，有什么可以帮你的？</p></div>';
    }else{
        msgs.forEach(m=>addMsg(m.text,m.who,false,m.time));
    }
    
    // 更新uid为当前对话的user_id（发送消息时使用）
    localStorage.setItem('chat_uid',convId);
    
    renderConvList();
}

function renderConvList(){
    const convs=getConversations();
    const list=document.getElementById('conv-list');
    list.innerHTML='';
    convs.forEach(c=>{
        const div=document.createElement('div');
        div.className='conv-item'+(c.id===currentConvId?' active':'');
        div.innerHTML='<div class="conv-preview">'+c.preview+'</div>';
        div.onclick=()=>switchConversation(c.id);
        list.appendChild(div);
    });
}

// 微信风格时间格式化
function formatTime(ts){
    const d=new Date(ts);
    const now=new Date();
    const h=d.getHours().toString().padStart(2,'0');
    const m=d.getMinutes().toString().padStart(2,'0');
    const timeStr=h+':'+m;
    
    // 今天的时间
    const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    const msgDay=new Date(d.getFullYear(),d.getMonth(),d.getDate());
    const diffDays=Math.floor((today-msgDay)/86400000);
    
    if(diffDays===0) return timeStr; // 今天只显示时间
    if(diffDays===1) return '昨天 '+timeStr;
    if(diffDays===2) return '前天 '+timeStr;
    
    // 本周内
    const dayOfWeek=d.getDay(); // 0=周日
    const weekNames=['周日','周一','周二','周三','周四','周五','周六'];
    if(diffDays<=7) return weekNames[dayOfWeek]+' '+timeStr;
    
    // 更久远显示完整日期
    return (d.getMonth()+1)+'/'+d.getDate()+' '+timeStr;
}

// 检查是否需要显示时间（超过3分钟才显示）
let lastMsgTime=0;
function shouldShowTime(ts){
    if(!lastMsgTime)return true;
    return (ts-lastMsgTime)>180000; // 3分钟=180000毫秒
}

function addMsg(text,who,save=true,timestamp){
    const welcome=messages.querySelector('.welcome');
    if(welcome)welcome.remove();
    
    const now=timestamp?new Date(timestamp):new Date();
    const ts=now.getTime();
    
    // 检查是否需要显示时间（超过3分钟）
    if(shouldShowTime(ts)){
        const timeDiv=document.createElement('div');
        timeDiv.style.cssText='text-align:center;color:#999;font-size:12px;margin:16px 0 8px';
        timeDiv.textContent=formatTime(ts);
        messages.appendChild(timeDiv);
        lastMsgTime=ts;
    }
    
    const div=document.createElement('div');div.className='msg '+who;
    const avatar=document.createElement('div');avatar.className='avatar';
    avatar.textContent=who==='user'?'我':'AI';
    const content=document.createElement('div');content.className='content';
    content.textContent=text;
    
    if(who==='user'){div.appendChild(content);div.appendChild(avatar);}
    else{div.appendChild(avatar);div.appendChild(content);}
    messages.appendChild(div);
    messages.scrollTop=messages.scrollHeight;
    
    if(save&&currentConvId){
        const msgs=getConvMessages(currentConvId);
        msgs.push({text,who,time:Date.now()});
        saveConvMessages(currentConvId,msgs);
        updateConvPreview();
    }
}

function addSystemMsg(text){
    const welcome=messages.querySelector('.welcome');
    if(welcome)welcome.remove();
    
    const div=document.createElement('div');
    div.style.cssText='text-align:center;color:#999;font-size:12px;margin:12px 0;padding:6px 12px;background:#f5f5f5;border-radius:12px;display:inline-block;max-width:80%;margin-left:auto;margin-right:auto;';
    div.textContent=text;
    const wrapper=document.createElement('div');
    wrapper.style.cssText='display:flex;justify-content:center;';
    wrapper.appendChild(div);
    messages.appendChild(wrapper);
    messages.scrollTop=messages.scrollHeight;
}

function updateConvPreview(){
    if(!currentConvId)return;
    const convs=getConversations();
    const msgs=getConvMessages(currentConvId);
    const lastMsg=msgs.length>0?msgs[msgs.length-1].text:'新对话';
    const idx=convs.findIndex(c=>c.id===currentConvId);
    if(idx>=0){convs[idx].preview=lastMsg.substring(0,30);convs[idx].time=Date.now();saveConversations(convs);renderConvList();}
}

async function send(){
    const text=input.value.trim();if(!text||isTyping)return;input.value='';
    if(!currentConvId)newConversation();
    addMsg(text,'user');
    
    isTyping=true;
    document.getElementById('typing').style.display='block';
    document.getElementById('send').disabled=true;
    document.getElementById('status').textContent='思考中...';
    
    // 每次发送时从localStorage读取最新的uid
    const currentUid=localStorage.getItem('chat_uid')||uid;
    
    try{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,user_id:currentUid})});
        const d=await r.json();
        if(d.no_reply){
            // AI 选择不回复，显示灰色提示
            addSystemMsg('对方已读不回');
        }else if(d.reply){
            // 拆分多条消息显示（模拟真人分段发消息）
            const parts=d.reply.split('\n\n');
            if(parts.length>1){
                parts.forEach((part,i)=>{
                    if(part.trim()){
                        setTimeout(()=>addMsg(part.trim(),'ai'),i*800);
                    }
                });
            }else{
                addMsg(d.reply,'ai');
            }
        }
    }catch(e){addMsg('发送失败，请重试','ai');}
    
    isTyping=false;
    document.getElementById('typing').style.display='none';
    document.getElementById('send').disabled=false;
    document.getElementById('status').textContent='就绪';
}

// 自动调整输入框高度
input.addEventListener('input',function(){
    this.style.height='auto';
    this.style.height=Math.min(this.scrollHeight,200)+'px';
});

input.onkeydown=e=>{
    if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}
};

// 主动消息轮询（支持延迟逐条发送）
async function checkPendingMessages(){
    try{
        const currentUid=localStorage.getItem('chat_uid')||uid;
        const r=await fetch('/api/pending_messages?user_id='+currentUid);
        const d=await r.json();
        if(d.messages && d.messages.length>0){
            // 显示系统提示线
            const divider=document.createElement('div');
            divider.style.cssText='text-align:center;color:#999;font-size:12px;margin:16px 0;position:relative';
            divider.innerHTML='<span style="background:#fff;padding:0 12px;position:relative;z-index:1">—— 你离开的这段时间 ——</span>';
            const line=document.createElement('div');
            line.style.cssText='position:absolute;top:50%;left:0;right:0;height:1px;background:#ddd';
            divider.style.position='relative';
            divider.insertBefore(line,divider.firstChild);
            messages.appendChild(divider);
            
            // 延迟逐条发送（模拟真人打字节奏）
            d.messages.forEach((m, i)=>{
                setTimeout(()=>{
                    addProactiveMsg(m.content, m.timestamp + i*2, m.silence_minutes);
                }, i * 1500); // 每条间隔1.5秒
            });
        }
    }catch(e){}
}

function addProactiveMsg(text,timestamp,silenceMinutes){
    const welcome=messages.querySelector('.welcome');
    if(welcome)welcome.remove();
    
    const now=new Date(timestamp*1000);
    const timeStr=now.getHours().toString().padStart(2,'0')+':'+now.getMinutes().toString().padStart(2,'0');
    
    const div=document.createElement('div');div.className='msg ai';
    const avatar=document.createElement('div');avatar.className='avatar';
    avatar.style.cssText='width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;background:#4a90d9;color:#fff;position:relative';
    avatar.textContent='AI';
    // 脉冲绿点
    const pulse=document.createElement('div');
    pulse.style.cssText='position:absolute;bottom:0;right:0;width:8px;height:8px;background:#52c41a;border-radius:50%;animation:pulse 2s infinite';
    avatar.appendChild(pulse);
    
    const content=document.createElement('div');content.className='content';
    content.style.cssText='max-width:70%;padding:12px 16px;border-radius:12px;font-size:14px;line-height:1.6;word-break:break-word;background:#f0f0f0;color:#000;border-bottom-left-radius:4px;margin-left:8px';
    content.textContent=text;
    
    const ts=document.createElement('div');ts.className='timestamp';
    ts.style.cssText='font-size:11px;color:#999;margin-top:4px;padding:0 8px;text-align:left';
    const timeAgo=Math.floor((Date.now()/1000)-timestamp);
    const timeAgoText=timeAgo>3600?Math.floor(timeAgo/3600)+'小时前':timeAgo>60?Math.floor(timeAgo/60)+'分钟前':'刚刚';
    ts.textContent=timeStr+' · 已发出'+timeAgoText;
    
    div.appendChild(avatar);div.appendChild(content);
    messages.appendChild(div);
    messages.appendChild(ts);
    messages.scrollTop=messages.scrollHeight;
}

// 脉冲动画
const style=document.createElement('style');
style.textContent='@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(82,196,26,0.7)}70%{box-shadow:0 0 0 6px rgba(82,196,26,0)}100%{box-shadow:0 0 0 0 rgba(82,196,26,0)}}';
document.head.appendChild(style);

// 导出聊天记录
function exportChat(){
    if(!currentConvId){alert('没有对话');return;}
    const msgs=getConvMessages(currentConvId);
    if(msgs.length===0){alert('没有聊天记录');return;}
    const lines=msgs.map(m=>{
        const d=new Date(m.time);
        const timeStr=d.getFullYear()+'/'+(d.getMonth()+1)+'/'+d.getDate()+' '+d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0');
        return '['+timeStr+'] '+(m.who==='user'?'我':'AI')+': '+m.text;
    });
    const text=lines.join('\n');
    const blob=new Blob([text],{type:'text/plain;charset=utf-8'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download='chat_'+new Date().toISOString().slice(0,10)+'.txt';
    a.click();
}

// 初始化（先从服务器加载历史对话）
loadFromServer().then(()=>{
    const convs=getConversations();
    if(convs.length>0){switchConversation(convs[0].id);}
    else{newConversation();}
});

// 启动时检查主动消息
checkPendingMessages();
// 每30秒轮询
setInterval(checkPendingMessages,30000);
</script></body></html>"""
