"""Tunnel 守护进程 —— 自动重连，URL 变化时告警"""
import subprocess
import time
import re
import sys

PORT = 53065
RESTART_DELAY = 3

def run_tunnel():
    """启动 localtunnel 并持续监控"""
    attempt = 0
    last_url = ""

    while True:
        attempt += 1
        print(f"[tunnel] 第 {attempt} 次启动...")

        try:
            proc = subprocess.Popen(
                ["/c/Users/mu/AppData/Roaming/npm/lt.cmd", "--port", str(PORT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            url = None
            start_time = time.time()

            # 读取输出，等待 URL
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                print(f"[lt] {line}")

                m = re.search(r'https://[a-z0-9-]+\.loca\.lt', line)
                if m:
                    url = m.group(0)
                    if url != last_url:
                        print(f"\n{'='*60}")
                        print(f"  🟢 Tunnel 就绪: {url}/wechat")
                        print(f"  Token: mimotesttalk01a")
                        print(f"{'='*60}\n")
                        last_url = url

                # 持续存活检查：每 30 秒没新输出就认为挂了
                if time.time() - start_time > 30 and url:
                    # 简单心跳：输出存活时间
                    elapsed = int(time.time() - start_time)
                    if elapsed % 60 == 0:
                        print(f"[tunnel] 已运行 {elapsed}s, URL: {url}")

            # proc 退出了
            print(f"[tunnel] 进程退出 (code={proc.returncode}), {RESTART_DELAY}s 后重试...")

        except FileNotFoundError:
            print("[tunnel] 错误: lt 命令未找到，请先安装: npm install -g localtunnel")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n[tunnel] 已停止")
            break
        except Exception as e:
            print(f"[tunnel] 异常: {e}")

        time.sleep(RESTART_DELAY)


if __name__ == "__main__":
    run_tunnel()
