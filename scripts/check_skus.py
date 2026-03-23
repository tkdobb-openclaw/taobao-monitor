#!/usr/bin/env python3
"""
检查特定商品的SKU配置
对比实际页面SKU和配置的关键词是否匹配
"""
import subprocess
import re
import time

# 需要检查的商品
CHECK_ITEMS = [
    ("667904575973", "岁老板", "Teric", ["黑色"]),
    ("629563113404", "三潜社", "Teric", ["黑色"]),
    ("632230014333", "三潜社", "Perdix", ["PERDIX 2 Ti BLACK"]),
    ("675444560376", "岁老板", "Perdix", ["Ti Black（钛黑版）"]),
]

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout.strip()

def get_skus():
    output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""")
    return [s.strip().strip('"') for s in output.split("|||") if s.strip()]

def get_price():
    output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""")
    output = output.strip('"')
    match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', output)
    return float(match.group(1).replace(',', '')) if match else None

def click_sku(idx):
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{idx}].click()" 2>/dev/null""")

print("="*60)
print("检查特定商品SKU配置")
print("="*60)

run("npx agent-browser state load data/taobao_auth.json 2>/dev/null")

for item_id, shop, model, target_skus in CHECK_ITEMS:
    print(f"\n【{shop} - {model}】")
    
    url = f"https://item.taobao.com/item.htm?id={item_id}"
    run(f'npx agent-browser open "{url}" 2>/dev/null')
    time.sleep(3)
    
    # 获取所有SKU
    skus = get_skus()
    print(f"  页面上的SKU ({len(skus)}个):")
    for i, sku in enumerate(skus):
        print(f"    [{i}] {sku}")
    
    # 检查配置的关键词是否匹配
    print(f"\n  配置关键词: {target_skus}")
    for target in target_skus:
        target_clean = target.lower().replace(' ', '')
        found = False
        for i, sku in enumerate(skus):
            sku_clean = sku.lower().replace(' ', '').replace('\\n', '')
            if target_clean in sku_clean:
                print(f"    ✓ '{target}' 匹配 [{i}] {sku[:30]}")
                # 点击获取价格
                click_sku(i)
                time.sleep(5)
                price = get_price()
                print(f"      价格: ¥{price}")
                found = True
                break
        if not found:
            print(f"    ✗ '{target}' 未找到匹配")

print("\n" + "="*60)
