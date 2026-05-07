#!/usr/bin/env python3
"""全量清洗启动脚本 - 通过Python直接启动后端并调用清洗接口"""
import os
import sys
import time
import subprocess
import requests
from threading import Thread

# 设置工作目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 从.env加载环境变量（优先使用.env，不存在则用.env.example）
env_file = '.env' if os.path.exists('.env') else '.env.example'
env_vars = {}
with open(env_file, 'r') as f:
    for line in f:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env_vars[key] = value

# 设置环境变量
for key, value in env_vars.items():
    os.environ[key] = value

print(f"环境变量已设置: MYSQL_HOST={os.environ.get('MYSQL_HOST')}")

# 启动uvicorn服务器
def run_server():
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'app.main:app',
        '--host', '0.0.0.0',
        '--port', '8808'
    ], cwd=os.path.dirname(os.path.abspath(__file__)))

# 后台启动服务器
server_thread = Thread(target=run_server, daemon=True)
server_thread.start()

# 等待服务器启动
print("等待服务器启动...")
max_wait = 30
for i in range(max_wait):
    try:
        resp = requests.get('http://localhost:8808/health', timeout=2)
        if resp.status_code == 200:
            print("服务器已就绪")
            break
    except:
        pass
    time.sleep(1)
    if i % 5 == 0:
        print(f"  等待中... ({i+1}/{max_wait})")

# 调用全量清洗接口
print("\n调用全量清洗接口...")
try:
    resp = requests.post('http://localhost:8808/api/stats/trigger-full-clean?batch_size=1000', timeout=300)
    print(f"响应状态: {resp.status_code}")
    print(f"响应内容: {resp.json()}")
except Exception as e:
    print(f"调用失败: {e}")

# 保持服务器运行以查看日志
print("\n服务器仍在运行，按 Ctrl+C 停止...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("已停止")