#!/usr/bin/env python3
"""测试两个修改后的商品"""
import subprocess
import re
import time
import json
from datetime import datetime
from pathlib import Path

def run(cmd, timeout=45):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""

def bring_to_front():
    script = '''
    tell application "Google Chrome"
        activate
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], timeout=5)
    except:
        pass

def get_skus():
    output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""", timeout=15)
    return [s.strip().strip('"') for s in output.split("|||") if s.strip()]

def click_sku(index):
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{index}].click()" 2>/dev/null""", timeout=10)

def get_price():
    output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""", timeout=10)
    match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', output)
    return float(match.group(1).replace(',', '')) if match else None

def find_sku_index(skus, target):
    target_clean = target.lower().replace(' ', '').replace('\n', '')
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\n', '')
        if target_clean in text_clean:
            return i
    return -1

# 只测试这两个商品
test_items = {
    "676780234187": {
        "shop": "大洋潜水",
        "model": "Perdix",
        "target_skus": ["perdix2 ti black 黑色"]
    },
    "676463247224": {
        "shop": "塞班户外",
        "model": "Perdix",
        "target_skus": ["PERDIX 2 Ti/古铜色/"]
    }
}

print("="*60)
print("📊 测试两个修改后的商品")
print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("="*60)

results = []

for item_id, rule in test_items.items():
    shop = rule['shop']
    model = rule['model']
    target_skus = rule['target_skus']
    url = f"https://item.taobao.com/item.htm?id={item_id}"
    
    print(f"\n【{shop} - {model}】")
    print(f"URL: {url}")
    
    # 打开页面
    run(f'npx agent-browser open "{url}" 2>/dev/null', timeout=30)
    time.sleep(4)
    bring_to_front()
    
    # 获取SKU
    skus = get_skus()
    print(f"  找到 {len(skus)} 个SKU:")
    for i, s in enumerate(skus[:5]):
        print(f"    [{i}] {s[:30]}")
    
    if not skus:
        print("  ❌ 未找到SKU")
        continue
    
    # 点击目标SKU
    for target in target_skus:
        idx = find_sku_index(skus, target)
        if idx < 0:
            print(f"  ❌ 未找到: {target}")
            print(f"     可用SKU: {[s[:20] for s in skus]}")
            continue
        
        print(f"  点击 [{idx}]: {target}")
        click_sku(idx)
        bring_to_front()
        time.sleep(5)
        
        price = get_price()
        if price:
            print(f"    ✅ ¥{price:.0f}")
            results.append({'shop': shop, 'sku': target, 'price': price})
        else:
            print(f"    ❌ 价格获取失败")
    
    time.sleep(2)

# 汇总
print("\n" + "="*60)
print("📊 测试结果")
print("="*60)
for r in results:
    print(f"  ¥{r['price']:>6.0f} - {r['shop']:8s} - {r['sku']}")

print(f"\n✅ 成功: {len(results)}/2")
print("="*60)
