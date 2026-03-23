#!/usr/bin/env python3
"""
调试点击和价格获取
"""
import subprocess
import re
import time

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

print("加载登录态...")
run("npx agent-browser state load data/taobao_auth.json 2>/dev/null")

print("访问页面...")
run('npx agent-browser open "https://item.taobao.com/item.htm?id=624281587175" 2>/dev/null')
time.sleep(3)

# 获取默认价格
price1 = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText" 2>/dev/null""")
print(f"默认价格: {price1}")

# 点击黑色经典版 (index 2)
print("\n点击黑色经典版 (index 2)...")
run("""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[2].click()" 2>/dev/null""")

print("等待 5 秒...")
time.sleep(5)

# 再次获取价格
price2 = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText" 2>/dev/null""")
print(f"点击后价格: {price2}")

# 检查是否选中了
selected = run("""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[2].className" 2>/dev/null""")
print(f"选中状态: {selected}")
