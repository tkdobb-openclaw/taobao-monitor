#!/usr/bin/env python3
"""测试错误检测功能"""
import subprocess
import re
import time
import json
from datetime import datetime

def run(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

# 测试一个商品
url = "https://item.taobao.com/item.htm?id=624281587175"
target_skus = ["黑色 TX 版", "灰色 DARK"]

print("="*60)
print("测试错误检测功能")
print("="*60)

# 打开页面
print(f"\n打开页面: {url}")
run(f'npx agent-browser open "{url}" 2>/dev/null', timeout=30)
time.sleep(3)

# 检查登录状态
title = run("npx agent-browser eval 'document.title' 2>/dev/null", timeout=10)
print(f"页面标题: {title}")

if '登录' in title or 'login' in title.lower():
    print("⚠️ 需要登录！")
else:
    print("✅ 登录状态正常")

# 获取SKU
sku_output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""", timeout=15)
skus = [s.strip().strip('"') for s in sku_output.split("|||") if s.strip()]

print(f"\n找到 {len(skus)} 个SKU:")
for i, s in enumerate(skus[:5]):
    print(f"  [{i}] {s[:30]}")

if not skus:
    print("❌ 错误: 未找到SKU元素！")
    print("可能原因:")
    print("  1. 页面未正确加载")
    print("  2. 淘宝页面结构变化")
    print("  3. 登录态失效")
else:
    # 测试点击
    print(f"\n测试点击 '灰色 DARK':")
    target = "灰色 DARK"
    target_clean = target.lower().replace(' ', '').replace('\n', '')
    idx = -1
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\n', '')
        if target_clean in text_clean:
            idx = i
            break
    
    if idx < 0:
        print(f"❌ 错误: 未找到SKU '{target}'")
    else:
        print(f"✅ 找到SKU索引: {idx}")
        run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{idx}].click()" 2>/dev/null""", timeout=10)
        time.sleep(3)
        
        # 获取价格
        price_output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""", timeout=10)
        print(f"价格文本: {price_output[:50]}")
        
        match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', price_output)
        if match:
            price = float(match.group(1).replace(',', ''))
            print(f"✅ 获取成功: ¥{price:.0f}")
        else:
            print("❌ 错误: 价格获取失败")

print("\n" + "="*60)
print("测试完成")
print("="*60)
