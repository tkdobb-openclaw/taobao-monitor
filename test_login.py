#!/usr/bin/env python3
"""测试淘宝页面加载"""
import subprocess
import time

def run(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

# 打开淘宝商品页面
url = "https://item.taobao.com/item.htm?id=695033055460"  # 塞班户外 Perdix
print(f"打开页面: {url}")
run(f'npx agent-browser open "{url}"', timeout=30)

# 等待更长时间
print("等待10秒...")
time.sleep(10)

# 检查页面标题
title = run("npx agent-browser eval 'document.title'", timeout=15)
print(f"页面标题: {title}")

# 检查是否有登录相关的元素
login_check = run('npx agent-browser eval "document.querySelector(\'.login-info-name\')?.innerText || \'未找到登录名\'"', timeout=15)
print(f"登录状态: {login_check}")

# 获取SKU列表
skus = run('npx agent-browser eval "Array.from(document.querySelectorAll(\'[class*=valueItem]\')).map(el => el.innerText).slice(0,5).join(\'|||\')"', timeout=15)
sku_display = skus[:200] if skus else '无'
print(f"SKU列表: {sku_display}")

# 截图查看
run('npx agent-browser screenshot /tmp/taobao_test.png', timeout=15)
print("截图已保存: /tmp/taobao_test.png")
