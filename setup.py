"""一键配置工具"""
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.py")
TOKEN_PATH = os.path.join(BASE_DIR, ".wechat_token")


def setup():
    print("=" * 50)
    print("  微信AI陪伴助手 - 一键配置")
    print("=" * 50)
    print()

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = f.read()

    # 获取当前 Token
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r") as f:
            current_token = f.read().strip()
    else:
        current_token = "未生成"

    print(f"当前 Token: {current_token}")
    print("(如果公众号后台已配置此 Token，直接回车跳过)")
    new_token = input("输入新 Token（可选）: ").strip()

    appid = input("请输入公众号 AppID: ").strip()
    if not appid:
        print("AppID 不能为空！")
        return

    appsecret = input("请输入公众号 AppSecret: ").strip()
    if not appsecret:
        print("AppSecret 不能为空！")
        return

    # 更新配置
    config = re.sub(r'WECHAT_APPID = ".*?"', f'WECHAT_APPID = "{appid}"', config)
    config = re.sub(r'WECHAT_APPSECRET = ".*?"', f'WECHAT_APPSECRET = "{appsecret}"', config)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(config)

    # 更新 Token
    if new_token:
        with open(TOKEN_PATH, "w") as f:
            f.write(new_token)
        token = new_token
    else:
        token = current_token

    print()
    print("=" * 50)
    print("  配置完成！")
    print("=" * 50)
    print()
    print(f"  AppID:     {appid}")
    print(f"  AppSecret: {appsecret[:8]}...")
    print(f"  Token:     {token}")
    print()
    print("下一步：")
    print("  1. 运行 python main.py 启动服务")
    print("  2. 去公众号后台配置服务器地址")
    print(f"  3. URL: http://你的公网IP:53065/wechat")
    print(f"  4. Token: {token}")
    print()


if __name__ == "__main__":
    setup()
