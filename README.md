# WeChat AI Companion

微信公众号 AI 陪伴助手 —— 基于 DeepSeek/MiMo API 的拟人化情感陪伴系统。

## 功能特性

- 🧠 **四层提示词架构**：灵魂层(L1) + 性格层(L2) + 记忆层(L3) + 上下文层(L4)
- 💾 **长期记忆系统**：跨会话记忆、用户画像、自动摘要
- 🎭 **情绪感知**：实时检测用户情绪，动态调整回复风格
- ⚡ **智能路由**：简单问候秒回、复杂对话调用 LLM
- 🔒 **安全防护**：速率限制、输入过滤、危机检测
- 🎨 **性格可调**：用户可通过指令实时调整 AI 语气（温柔/傲娇/活泼等）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 填入真实值：

```env
# 微信公众号配置
WECHAT_TOKEN=your-wechat-token
WECHAT_APPID=wx-your-appid
WECHAT_APPSECRET=your-appsecret

# API 配置（MiMo 或 DeepSeek）
DEEPSEEK_API_KEY=tp-your-api-key
DEEPSEEK_API_URL=https://token-plan-cn.xiaomimimo.com/v1/chat/completions
DEEPSEEK_MODEL=mimo-v2.5-pro
```

### 3. 启动服务

```bash
python main.py
```

服务默认运行在 `http://0.0.0.0:53065`。

### 4. 配置微信公众号

在微信公众号后台 → 开发 → 基本配置 → 服务器配置：

- **URL**: `http://你的公网IP:53065/wechat`
- **Token**: 与 `.env` 中 `WECHAT_TOKEN` 一致
- **EncodingAESKey**: 随机生成
- **消息加解密方式**: 明文模式

## 项目结构

```
├── main.py              # 主入口（FastAPI + 微信消息处理）
├── ai.py                # AI 对话核心（API 调用 + 回复生成）
├── engine.py            # 引擎（情绪检测 + 意图识别 + Prompt 构建）
├── config.py            # 配置（从环境变量读取敏感信息）
├── soul_layer.py        # 灵魂层（四层提示词 L1-L4）
├── memory.py            # 聊天记录存储（SQLite）
├── auto_memory.py       # 自动记忆提取（用户画像 + 偏好）
├── human_memory.py      # 人类化记忆系统（遗忘曲线 + 情感权重）
├── mood.py              # AI 情绪引擎
├── safety.py            # 安全过滤 + 危机检测
├── token_optimizer.py   # Token 压缩（无限历史 + 分级压缩）
├── reply_fallback.py    # 灾备兜底回复
├── wechat_api.py        # 微信客服消息 API
├── config.example.py    # 配置模板
├── .env.example         # 环境变量模板
├── requirements.txt     # Python 依赖
└── start.bat            # Windows 一键启动
```

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/wechat` | GET | 微信服务器验证 |
| `/wechat` | POST | 接收微信消息 |
| `/health` | GET | 健康检查 |
| `/test` | GET | 网页测试界面 |
| `/api/chat` | POST | API 对话接口 |

## Docker 部署

```bash
docker build -t wechat-ai .
docker run -d --env-file .env -p 53065:53065 wechat-ai
```

## 隧道工具（本地开发）

本地开发时需要内网穿透工具将本地端口暴露到公网：

- [ngrok](https://ngrok.com/) — 稳定，需注册
- [localtunnel](https://localtunnel.me/) — 免费，`npx localtunnel --port 53065`
- [natapp](https://natapp.cn/) — 国内稳定，免费隧道

## 技术栈

- **框架**: FastAPI + Uvicorn
- **AI**: MiMo v2.5-pro / DeepSeek Chat（通过 OpenAI 兼容 API）
- **存储**: SQLite（聊天记录 + 记忆系统）
- **协议**: 微信被动回复 XML

## License

MIT
