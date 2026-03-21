#!/usr/bin/env python3
"""
淘宝价格监控 - Python完整版
自动匹配SKU关键词，获取价格
"""
import subprocess
import json
import re
import time
from pathlib import Path
from datetime import datetime

# 加载配置
CONFIG_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/config.json").expanduser()
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

def run(cmd, timeout=30):
    """运行shell命令"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()

def get_skus():
    """获取所有SKU文本"""
    output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""")
    return [s.strip().strip('"') for s in output.split("|||") if s.strip()]

def click_sku(index):
    """点击指定索引的SKU"""
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{index}].click()" 2>/dev/null""")

def get_price():
    """获取当前价格"""
    output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""")
    output = output.strip('"')
    match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', output)
    return float(match.group(1).replace(',', '')) if match else None

def find_sku_index(skus, target):
    """根据关键词查找SKU索引"""
    target_clean = target.lower().replace(' ', '').replace('\n', '')
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\n', '')
        if target_clean in text_clean:
            return i
    return -1

def main():
    print("=" * 60)
    print(f"📊 淘宝价格监控 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 加载登录态
    run("npx agent-browser state load data/taobao_auth.json 2>/dev/null")
    
    results = []
    sku_rules = CONFIG.get('sku_rules', {})
    
    for item_id, rule in sku_rules.items():
        shop = rule['shop']
        model = rule['model']
        target_skus = rule['target_skus']
        
        print(f"\n【{shop} - {model}】")
        
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        run(f'npx agent-browser open "{url}" 2>/dev/null')
        time.sleep(3)
        
        # 获取页面SKU列表
        skus = get_skus()
        print(f"  找到 {len(skus)} 个SKU")
        
        item_result = {
            'shop': shop,
            'model': model,
            'item_id': item_id,
            'skus': []
        }
        
        # 匹配并点击每个目标SKU
        for target in target_skus:
            idx = find_sku_index(skus, target)
            if idx >= 0:
                print(f"  点击 [{idx}]: {target}")
                click_sku(idx)
                time.sleep(6)
                
                price = get_price()
                if price:
                    print(f"    ✅ ¥{price:.0f}")
                    item_result['skus'].append({'name': target, 'price': price})
                else:
                    print(f"    ❌ 获取失败")
            else:
                print(f"  ❌ 未找到: {target}")
        
        results.append(item_result)
    
    # 输出汇总
    print("\n" + "=" * 60)
    print("📊 价格汇总")
    print("=" * 60)
    
    for r in results:
        print(f"\n【{r['model']} - {r['shop']}】")
        for sku in r['skus']:
            print(f"  ¥{sku['price']:>6.0f} - {sku['name']}")
    
    # 保存JSON
    output_file = Path(f"logs/prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(output_file, 'w') as f:
        json.dump({'time': datetime.now().isoformat(), 'results': results}, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存: {output_file}")
    print("=" * 60)

if __name__ == '__main__':
    main()
