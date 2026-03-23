#!/usr/bin/env python3
"""
淘宝价格监控 - 可视化版本（Mac前台显示）
每次操作后自动将浏览器窗口带到前台
"""
import subprocess
import re
import time
import json
from datetime import datetime
from pathlib import Path

def run(cmd, timeout=45):
    """运行命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ 超时")
        return ""
    except Exception as e:
        return ""

def bring_to_front():
    """将 Chrome 窗口带到前台"""
    # 使用 AppleScript 激活 Chrome
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
    """获取SKU列表"""
    output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""", timeout=15)
    return [s.strip().strip('"') for s in output.split("|||") if s.strip()]

def click_sku(index):
    """点击SKU"""
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{index}].click()" 2>/dev/null""", timeout=10)

def get_price():
    """获取价格"""
    output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""", timeout=10)
    match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', output)
    return float(match.group(1).replace(',', '')) if match else None

def find_sku_index(skus, target):
    """查找SKU索引"""
    target_clean = target.lower().replace(' ', '').replace('\n', '')
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\n', '')
        if target_clean in text_clean:
            return i
    return -1

def is_tx_version(sku_name):
    """判断是否为TX版本"""
    return 'tx' in sku_name.lower()

def fetch_product(url, target_skus, shop, model):
    """抓取单个商品"""
    print(f"\n【{shop} - {model}】")
    
    # 打开页面并带到前台
    run(f'npx agent-browser open "{url}" 2>/dev/null', timeout=30)
    time.sleep(3)
    bring_to_front()  # 激活窗口
    time.sleep(2)
    
    # 获取SKU列表
    skus = get_skus()
    print(f"  找到 {len(skus)} 个SKU")
    
    if not skus:
        print(f"  ❌ 页面加载失败")
        return None
    
    item_result = {'shop': shop, 'model': model, 'skus': [], 'skus_tx': []}
    
    # 点击每个目标SKU
    for target in target_skus:
        idx = find_sku_index(skus, target)
        if idx < 0:
            print(f"  ❌ 未找到: {target}")
            continue
        
        print(f"  点击 [{idx}]: {target}")
        click_sku(idx)
        bring_to_front()  # 点击后激活窗口
        time.sleep(5)
        
        price = get_price()
        if price:
            print(f"    ✅ ¥{price:.0f}")
            sku_data = {'name': target, 'price': price, 'shop': shop}
            if is_tx_version(target):
                item_result['skus_tx'].append(sku_data)
            else:
                item_result['skus'].append(sku_data)
        else:
            print(f"    ❌ 获取失败")
    
    return item_result

# 加载配置
CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

sku_rules = CONFIG.get('sku_rules', {})

print("="*60)
print(f"📊 淘宝价格监控 - Mac可视化版本")
print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"商品数: {len(sku_rules)}")
print("="*60)

# 检查浏览器
title = run("npx agent-browser eval 'document.title' 2>/dev/null", timeout=10)
if not title:
    print("\n❌ 浏览器未运行！")
    print("请先运行: npx agent-browser --headed open about:blank")
    exit(1)

print(f"✅ 浏览器已连接")
bring_to_front()  # 初始激活
print("="*60)

results = []
items = list(sku_rules.items())

for i, (item_id, rule) in enumerate(items):
    # 不再重启浏览器，一次跑完
    
    shop = rule['shop']
    model = rule['model']
    target_skus = rule['target_skus']
    url = f"https://item.taobao.com/item.htm?id={item_id}"
    
    result = fetch_product(url, target_skus, shop, model)
    if result:
        results.append(result)

# 汇总 - 统一表格格式
print("\n" + "="*70)
print("📊 价格汇总（统一表格）")
print("="*70)

from collections import defaultdict
by_model = defaultdict(lambda: {'normal': [], 'tx': []})

for r in results:
    model = r['model']
    by_model[model]['normal'].extend(r.get('skus', []))
    by_model[model]['tx'].extend(r.get('skus_tx', []))

def print_table(title, skus_list):
    """打印统一格式表格"""
    if not skus_list:
        return
    
    prices = [s['price'] for s in skus_list]
    min_p, max_p = min(prices), max(prices)
    
    print(f"\n【{title}】")
    print("-" * 70)
    print(f"{'店铺':<10} {'SKU名称':<25} {'价格':>10} {'标记':<6}")
    print("-" * 70)
    
    for sku in sorted(skus_list, key=lambda x: x['price']):
        if sku['price'] == min_p:
            symbol = "⬇️最低"
        elif sku['price'] == max_p:
            symbol = "⬆️最高"
        else:
            symbol = ""
        
        name = sku['name'][:22] + ".." if len(sku['name']) > 25 else sku['name']
        print(f"{sku['shop']:<10} {name:<25} ¥{sku['price']:>8.0f} {symbol:<6}")
    
    print("-" * 70)

# 打印各型号表格
for model in ['Perdix', 'Peregrine', 'Teric', 'Tern']:
    if model not in by_model:
        continue
    
    normal_skus = by_model[model]['normal']
    tx_skus = by_model[model]['tx']
    
    if normal_skus:
        print_table(f"{model} - 普通版", normal_skus)
    
    if tx_skus:
        print_table(f"{model} - TX版本", tx_skus)

# 保存
output_file = Path(f"logs/prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
output_file.parent.mkdir(exist_ok=True)
with open(output_file, 'w') as f:
    json.dump({'time': datetime.now().isoformat(), 'total': len(sku_rules), 'success': len(results), 'results': results}, f, indent=2, ensure_ascii=False)

print(f"\n{'='*70}")
print(f"💾 结果已保存: {output_file}")
print(f"✅ 成功: {len(results)}/{len(sku_rules)}")
print(f"{'='*70}")
