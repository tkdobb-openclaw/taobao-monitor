#!/usr/bin/env python3
"""快速测试 - 只抓取5个Perdix商品"""
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

# 只测试5个Perdix商品
sku_rules = {
    "676780234187": {"shop": "大洋潜水", "model": "Perdix", "target_skus": ["perdix2 ti 银色"]},
    "676463247224": {"shop": "塞班户外", "model": "Perdix", "target_skus": ["PERDIX 2 Ti/银色/"]},
    "544005716799": {"shop": "白鳍鲨", "model": "Perdix", "target_skus": ["PERDIX 2 Ti BLACK"]},
    "675444560376": {"shop": "岁老板", "model": "Perdix", "target_skus": ["Ti Black（钛黑版）"]},
    "632230014333": {"shop": "三潜社", "model": "Perdix", "target_skus": ["PERDIX 2 Ti BLACK"]},
}

print("="*60)
print(f"📊 淘宝价格监控 - 5商品测试")
print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("="*60)

results = []

for item_id, rule in sku_rules.items():
    shop = rule['shop']
    model = rule['model']
    target_skus = rule['target_skus']
    
    print(f"\n【{shop} - {model}】")
    
    url = f"https://item.taobao.com/item.htm?id={item_id}"
    
    # 打开页面
    run(f'npx agent-browser open "{url}" 2>/dev/null', timeout=30)
    time.sleep(4)
    
    # 获取SKU列表
    sku_output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""", timeout=15)
    skus = [s.strip().strip('"') for s in sku_output.split("|||") if s.strip()]
    print(f"  找到 {len(skus)} 个SKU")
    
    if not skus:
        print(f"  ❌ 页面加载失败")
        continue
    
    item_result = {'shop': shop, 'model': model, 'skus': []}
    
    # 点击每个目标SKU
    for target in target_skus:
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
        run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{idx}].click()" 2>/dev/null""", timeout=10)
        time.sleep(5)
        
        # 获取价格
        price_output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""", timeout=10)
        match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', price_output)
        if match:
            price = float(match.group(1).replace(',', ''))
            print(f"    ✅ ¥{price:.0f}")
            item_result['skus'].append({'name': target, 'price': price})
        else:
            print(f"    ❌ 获取失败: {price_output[:50]}")
    
    results.append(item_result)
    time.sleep(2)

# 汇总
print("\n" + "="*60)
print("📊 价格汇总")
print("="*60)

for r in results:
    print(f"\n【{r['model']} - {r['shop']}】")
    for sku in r['skus']:
        print(f"  ¥{sku['price']:>6.0f} - {sku['name']}")

# 保存
output_file = Path(f"logs/test_5_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
output_file.parent.mkdir(exist_ok=True)
with open(output_file, 'w') as f:
    json.dump({'time': datetime.now().isoformat(), 'results': results}, f, indent=2, ensure_ascii=False)

print(f"\n💾 结果已保存: {output_file}")
print("="*60)
