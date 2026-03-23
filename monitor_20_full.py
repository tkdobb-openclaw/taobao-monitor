#!/usr/bin/env python3
"""
淘宝价格监控 - 20商品完整版（改进版）
- Tern TX / Peregrine TX 单独分类
- 标记最低价和最高价
"""
import subprocess
import re
import time
import json
import os
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

def restart_browser():
    """重启浏览器"""
    print("  🔄 重启浏览器...")
    run("npx agent-browser close 2>/dev/null", timeout=10)
    time.sleep(2)
    run(f'npx agent-browser state load data/taobao_auth.json 2>/dev/null', timeout=15)
    time.sleep(1)

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
    """抓取单个商品（带错误检测）"""
    print(f"\n【{shop} - {model}】")
    
    # 打开页面
    run(f'npx agent-browser open "{url}" 2>/dev/null', timeout=30)
    time.sleep(4)
    
    # 检查是否需要登录
    title = run("npx agent-browser eval 'document.title' 2>/dev/null", timeout=10)
    if '登录' in title or 'login' in title.lower():
        print(f"  ⚠️ 需要登录！当前页面: {title}")
        return {'error': 'need_login', 'shop': shop, 'model': model}
    
    # 获取SKU列表
    skus = get_skus()
    print(f"  找到 {len(skus)} 个SKU")
    
    if not skus:
        print(f"  ❌ 未找到SKU元素！可能原因：")
        print(f"     1. 页面未正确加载")
        print(f"     2. 淘宝页面结构变化")
        print(f"     3. 商品已下架")
        return {'error': 'no_sku', 'shop': shop, 'model': model}
    
    item_result = {
        'shop': shop, 
        'model': model, 
        'skus': [],
        'skus_tx': [],
        'errors': []
    }
    
    # 点击每个目标SKU
    for target in target_skus:
        idx = find_sku_index(skus, target)
        if idx < 0:
            print(f"  ❌ 未找到SKU: '{target}'")
            print(f"     可用SKU: {[s[:20] for s in skus[:3]]}...")
            item_result['errors'].append(f'未找到: {target}')
            continue
        
        print(f"  点击 [{idx}]: {target}")
        click_sku(idx)
        time.sleep(5)
        
        price = get_price()
        if price:
            print(f"    ✅ ¥{price:.0f}")
            sku_data = {'name': target, 'price': price, 'shop': shop}
            
            # TX版本单独分类
            if is_tx_version(target):
                item_result['skus_tx'].append(sku_data)
            else:
                item_result['skus'].append(sku_data)
        else:
            print(f"    ❌ 价格获取失败")
            item_result['errors'].append(f'价格获取失败: {target}')
    
    return item_result

# 加载配置
CONFIG_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/config.json").expanduser()
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

sku_rules = CONFIG.get('sku_rules', {})

print("="*60)
print(f"📊 淘宝价格监控 - 20商品完整版")
print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"商品数: {len(sku_rules)}")
print("="*60)

# 初始加载登录态
restart_browser()

results = []
items = list(sku_rules.items())

for i, (item_id, rule) in enumerate(items):
    # 每5个商品重启一次浏览器
    if i > 0 and i % 5 == 0:
        restart_browser()
    
    shop = rule['shop']
    model = rule['model']
    target_skus = rule['target_skus']
    url = f"https://item.taobao.com/item.htm?id={item_id}"
    
    result = fetch_product(url, target_skus, shop, model)
    if result:
        results.append(result)
    
    time.sleep(2)

# 汇总 - 按品类分组并标记最低/最高价
print("\n" + "="*60)
print("📊 价格汇总")
print("="*60)

# 按型号分组
from collections import defaultdict
by_model = defaultdict(lambda: {'normal': [], 'tx': []})

for r in results:
    model = r['model']
    by_model[model]['normal'].extend(r.get('skus', []))
    by_model[model]['tx'].extend(r.get('skus_tx', []))

# 打印汇总
for model in ['Perdix', 'Peregrine', 'Teric', 'Tern']:
    if model not in by_model:
        continue
    
    normal_skus = by_model[model]['normal']
    tx_skus = by_model[model]['tx']
    
    print(f"\n【{model}】")
    
    # 普通版本
    if normal_skus:
        normal_prices = [s['price'] for s in normal_skus]
        min_price = min(normal_prices)
        max_price = max(normal_prices)
        
        print(f"  普通版:")
        for sku in sorted(normal_skus, key=lambda x: x['price']):
            symbol = ""
            if sku['price'] == min_price:
                symbol = "⬇️最低"  # 最低价
            elif sku['price'] == max_price:
                symbol = "⬆️最高"  # 最高价
            print(f"    ¥{sku['price']:>6.0f} - {sku['shop']:8s} {symbol}")
    
    # TX版本（单独分类）
    if tx_skus:
        tx_prices = [s['price'] for s in tx_skus]
        min_tx = min(tx_prices)
        max_tx = max(tx_prices)
        
        print(f"  TX版本:")
        for sku in sorted(tx_skus, key=lambda x: x['price']):
            symbol = ""
            if sku['price'] == min_tx:
                symbol = "⬇️最低"
            elif sku['price'] == max_tx:
                symbol = "⬆️最高"
            print(f"    ¥{sku['price']:>6.0f} - {sku['shop']:8s} {symbol}")

# 统计错误
errors = [r for r in results if r.get('error')]
success_count = len([r for r in results if not r.get('error')])

# 保存
output_file = Path(f"logs/prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
output_file.parent.mkdir(exist_ok=True)
with open(output_file, 'w') as f:
    json.dump({
        'time': datetime.now().isoformat(),
        'total': len(sku_rules),
        'success': success_count,
        'errors': len(errors),
        'results': results
    }, f, indent=2, ensure_ascii=False)

print(f"\n💾 结果已保存: {output_file}")
print(f"✅ 成功: {success_count}/{len(sku_rules)}")
if errors:
    print(f"❌ 失败: {len(errors)}个")
    for e in errors[:3]:
        print(f"   - {e.get('shop')} {e.get('model')}: {e.get('error')}")
print("="*60)
