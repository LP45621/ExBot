# 微信公众号 AI 陪伴助手

## 项目结构
```
wechat-ai/
├── main.py          # 服务入口，端口 53065
├── ai.py            # AI 模块（MiMo API + 话术库）
├── memory.py        # SQLite 对话记忆系统
├── script_db.py     # 话术库管理器
├── scripts.json     # 话术数据（177条）
├── scripts.db       # 话术数据库
├── config.py        # 配置文件
├── setup.py         # 一键配置工具
├── start.bat        # 一键启动
├── test.py          # 测试脚本
└── README.md        # 本文件
```

## 快速开始

### 1. 启动服务
双击 `start.bat` 或运行：
```bash
python main.py
```

### 2. 配置公众号
运行一键配置工具：
```bash
python setup.py
```
按提示输入 AppID、AppSecret、Token。

### 3. 公众号后台配置
1. 打开 https://developers.weixin.qq.com
2. 找到你的公众号应用
3. 配置服务器地址：
   - URL: `http://你的公网IP:53065/wechat`
   - Token: 你在 setup.py 中设置的 Token
   - EncodingAESKey: 随机生成

### 4. 内网穿透（本地测试）
```bash
# 安装 cpolar
pip install cpolar

# 启动隧道
cpolar http 53065
```

## 功能特性
- 177 条话术库（问候、情绪、闲聊、撒娇、关心等）
- 情绪识别（开心、难过、生气、累了等）
- 意图识别（早安、晚安、吃饭、天气等）
- 对话记忆（SQLite 存储）
- 自动摘要（超过 30 条对话自动总结）
- MiMo API 接入（小米模型）

## 注意事项
- 公众号需认证才能用服务器模式
- 每次回复必须 5 秒内返回
- 本地测试需要内网穿透
