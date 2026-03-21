#!/usr/bin/env python3
"""
淘宝价格监控 - 带调试
"""
import subprocess
import time
from datetime import datetime

def run(cmd, timeout=30):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()

print("=" * 50)
print(f"淘宝价格监控 - {datetime.now().strftime('%H:%M')}")
print("=" * 50)

run("npx agent-browser state load data/taobao_auth.json 2>/dev/null")

url = "https://item.taobao.com/item.htm?id=624281587175"
print(f"\n访问: 塞班户外 - Peregrine")
run(f'npx agent-browser open "{url}" 2>/dev/null')
time.sleep(3)

# 获取所有 SKU
skus = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""").split("|||")
skus = [s.strip().strip('"') for s in skus if s.strip()]
print(f"找到 {len(skus)} 个 SKU")

# 点击 黑色经典版
target_idx = 2
print(f"\n点击 SKU[{target_idx}]: {skus[target_idx]}")
run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{target_idx}].click()" 2>/dev/null""")

print("等待价格更新...")
time.sleep(5)

# 获取价格 - 尝试多种方式
print("\n尝试获取价格:")

# 方式1
price1 = run("""npx agent-browser eval "document.querySelector('[class*=\\'priceText--\\']')?.innerText" 2>/dev/null""")
print(f"  方式1 (priceText): {price1}")

# 方式2  
price2 = run("""npx agent-browser eval "document.querySelector('.tb-rmb-num')?.innerText" 2>/dev/null""")
print(f"  方式2 (tb-rmb-num): {price2}")

# 方式3
price3 = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText" 2>/dev/null""")
print(f"  方式3 (Price--): {price3}")

# 方式4: 所有包含 ¥ 的文本
price4 = run("""npx agent-browser eval "const els = document.querySelectorAll('*'); for (let el of els) { if (el.children.length === 0 && el.innerText?.includes('¥')) return el.innerText; }" 2>/dev/null""")
print(f"  方式4 (搜索¥): {price4[:50] if price4 else 'N/A'}")

print("\n" + "=" * 50)
