#!/usr/bin/env python3
"""
淘宝价格监控 - 修复版
"""
import subprocess
import re
import time
from datetime import datetime

ITEMS = {
    "624281587175": {
        "shop": "塞班户外",
        "model": "Peregrine", 
        "skus": [("黑色 TX 版", 3), ("黑色经典版", 2), ("灰色 DARK", 1)]
    }
}

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

def get_price():
    """获取价格"""
    output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""")
    output = output.strip('"')
    match = re.search(r'¥\s*([\d,]+\.?\d*)', output)
    return float(match.group(1).replace(',', '')) if match else None

def main():
    print("=" * 50)
    print(f"📊 淘宝价格监控 - {datetime.now().strftime('%H:%M')}")
    print("=" * 50)
    
    run("npx agent-browser state load data/taobao_auth.json 2>/dev/null")
    
    for item_id, config in ITEMS.items():
        shop, model, skus = config["shop"], config["model"], config["skus"]
        print(f"\n【{shop} - {model}】")
        
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        run(f'npx agent-browser open "{url}" 2>/dev/null')
        time.sleep(3)
        
        for name, idx in skus:
            # 点击
            run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{idx}].click()" 2>/dev/null""")
            time.sleep(4)
            
            # 获取价格
            price = get_price()
            if price:
                print(f"  ¥{price:>6.0f} - {name}")
            else:
                print(f"  失败 - {name}")
    
    print("\n" + "=" * 50)
    print("✅ 完成")

if __name__ == '__main__':
    main()
