#!/usr/bin/env python3
"""快速测试SKU抓取 - 只测试一个商品"""
import subprocess
import re
import time
import json

def run(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

# 关闭现有浏览器
run("npx agent-browser close 2>/dev/null", timeout=10)
time.sleep(1)

# 加载登录态
run("npx agent-browser state load data/taobao_auth.json 2>/dev/null", timeout=15)

# 测试商品: 塞班户外 Peregrine
url = "https://item.taobao.com/item.htm?id=624281587175"
target_skus = ["黑色 TX 版", "黑色经典版", "灰色 DARK"]

print("="*60)
print("测试商品: 塞班户外 - Peregrine")
print("="*60)

# 打开页面
print(f"\n打开页面...")
run(f'npx agent-browser open "{url}" 2>/dev/null', timeout=30)
time.sleep(4)

# 获取标题
title = run("npx agent-browser eval 'document.title' 2>/dev/null", timeout=10)
print(f"标题: {title}")

# 获取SKU列表
print(f"\n获取SKU列表...")
sku_output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""", timeout=15)
skus = [s.strip() for s in sku_output.split("|||") if s.strip()]
print(f"找到 {len(skus)} 个SKU:")
for i, s in enumerate(skus[:5]):
    print(f"  [{i}] {s}")

# 点击并获取价格
print(f"\n点击目标SKU获取价格...")
results = []

for target in target_skus:
    # 查找SKU索引
    target_clean = target.lower().replace(' ', '').replace('\n', '')
    idx = -1
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\n', '')
        if target_clean in text_clean:
            idx = i
            break
    
    if idx < 0:
        print(f"  ❌ 未找到: {target}")
        continue
    
    print(f"  点击 [{idx}]: {target}")
    
    # 点击
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{idx}].click()" 2>/dev/null""", timeout=10)
    time.sleep(5)
    
    # 获取价格
    price_output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""", timeout=10)
    
    # 解析价格
    match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', price_output)
    if match:
        price = float(match.group(1).replace(',', ''))
        print(f"    ✅ ¥{price:.0f}")
        results.append({'sku': target, 'price': price})
    else:
        print(f"    ❌ 获取失败: {price_output[:50]}")

# 汇总
print("\n" + "="*60)
print("结果汇总:")
print("="*60)
for r in results:
    print(f"  ¥{r['price']:>6.0f} - {r['sku']}")

print(f"\n成功: {len(results)}/{len(target_skus)}")
