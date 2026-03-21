#!/usr/bin/env python3
"""
淘宝价格监控 - 最终版
"""
import subprocess
import re
import time
from datetime import datetime

ITEMS = {
    "624281587175": {
        "shop": "塞班户外",
        "model": "Peregrine", 
        "skus": ["黑色 TX 版", "黑色经典版", "灰色 DARK"]
    }
}

def run(cmd, timeout=30):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()

def get_skus():
    output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""")
    return [s.strip().strip('"') for s in output.split("|||") if s.strip()]

def click_sku(index):
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{index}].click()" 2>/dev/null""")

def get_price():
    """获取价格并提取数字"""
    output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || 'N/A'" 2>/dev/null""")
    output = output.strip('"')
    
    # 提取价格数字
    match = re.search(r'¥\s*([\d,]+\.?\d*)', output)
    if match:
        return float(match.group(1).replace(',', ''))
    return None

def find_index(skus, target):
    target_clean = target.lower().replace(' ', '')
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\\n', '')
        if target_clean in text_clean:
            return i
    return -1

def main():
    print("=" * 50)
    print(f"📊 淘宝价格监控 - {datetime.now().strftime('%H:%M')}")
    print("=" * 50)
    
    run("npx agent-browser state load data/taobao_auth.json 2>/dev/null")
    
    for item_id, config in ITEMS.items():
        shop, model, targets = config["shop"], config["model"], config["skus"]
        print(f"\n【{shop} - {model}】")
        
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        run(f'npx agent-browser open "{url}" 2>/dev/null')
        time.sleep(3)
        
        skus = get_skus()
        
        for target in targets:
            idx = find_index(skus, target)
            if idx >= 0:
                click_sku(idx)
                time.sleep(4)
                price = get_price()
                if price:
                    print(f"  ¥{price:>6.0f} - {target}")
                else:
                    print(f"  获取失败 - {target}")
            else:
                print(f"  ✗ 未找到 - {target}")
    
    print("\n" + "=" * 50)
    print("✅ 完成")

if __name__ == '__main__':
    main()
