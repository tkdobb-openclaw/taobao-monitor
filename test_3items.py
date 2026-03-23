#!/usr/bin/env python3
"""快速测试 - 只抓取前3个商品"""
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

# 配置
sku_rules = {
    "676780234187": {"shop": "大洋潜水", "model": "Perdix", "target_skus": ["perdix2 ti 银色"]},
    "624281587175": {"shop": "塞班户外", "model": "Peregrine", "target_skus": ["黑色 TX 版", "黑色经典版", "灰色 DARK"]},
    "584863170468": {"shop": "大洋潜水", "model": "Teric", "target_skus": ["浅灰色"]},
}

print("="*60)
print(f"📊 淘宝价格监控测试 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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
    time.sleep(3)
    
    # 获取SKU列表
    sku_output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""", timeout=15)
    skus = [s.strip().strip('"') for s in sku_output.split("|||") if s.strip()]
    print(f"  找到 {len(skus)} 个SKU")
    
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
            print(f"    ❌ 获取失败")
    
    results.append(item_result)

# 汇总
print("\n" + "="*60)
print("📊 价格汇总")
print("="*60)

for r in results:
    print(f"\n【{r['model']} - {r['shop']}】")
    for sku in r['skus']:
        print(f"  ¥{sku['price']:>6.0f} - {sku['name']}")

# 保存
output_file = Path(f"logs/prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
output_file.parent.mkdir(exist_ok=True)
with open(output_file, 'w') as f:
    json.dump({'time': datetime.now().isoformat(), 'results': results}, f, indent=2, ensure_ascii=False)

print(f"\n💾 结果已保存: {output_file}")
print("="*60)
