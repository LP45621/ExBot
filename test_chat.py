"""网页测试界面 —— 浏览器直接聊，不走微信"""
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ai import get_ai_reply
from engine import split_reply


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
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f5f5f5;height:100vh;display:flex;flex-direction:column}
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
<div id="chat"></div>
<div id="input-area">
<input id="input" placeholder="说点什么..." autocomplete="off">
<button id="send">发送</button>
</div>
<script>
const chat=document.getElementById('chat'),input=document.getElementById('input');
const uid='web-'+Date.now();
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
    }catch(e){removeTyping();addMsg('发送失败','ai');}
}
document.getElementById('send').onclick=send;
input.onkeydown=e=>{if(e.key==='Enter')send()};
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
