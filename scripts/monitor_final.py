#!/usr/bin/env python3
"""
淘宝价格监控 - agent-browser 完整版
点击 SKU 获取真实价格
"""
import subprocess
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
    """获取所有 SKU"""
    output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""")
    return [s.strip().strip('"') for s in output.split("|||") if s.strip()]

def click_sku(index):
    """点击 SKU"""
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{index}].click()" 2>/dev/null""")

def get_price():
    """获取价格"""
    output = run("""npx agent-browser eval "const el = document.querySelector('[class*=\\'priceText--\\']'); el ? el.innerText.match(/¥\\s*([\\d,]+)/)?.[1] || el.innerText.substring(0,20) : 'N/A'" 2>/dev/null""")
    return output.strip('"')

def find_index(skus, target):
    """查找 SKU 索引"""
    target_clean = target.lower().replace(' ', '')
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\\n', '')
        if target_clean in text_clean:
            return i
    return -1

def main():
    print("=" * 50)
    print(f"淘宝价格监控 - {datetime.now().strftime('%H:%M')}")
    print("=" * 50)
    
    run("npx agent-browser state load data/taobao_auth.json 2>/dev/null")
    
    for item_id, config in ITEMS.items():
        shop, model, targets = config["shop"], config["model"], config["skus"]
        print(f"\n【{shop} - {model}】")
        
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        run(f'npx agent-browser open "{url}" 2>/dev/null')
        time.sleep(3)
        
        skus = get_skus()
        print(f"  共 {len(skus)} 个 SKU")
        
        for target in targets:
            idx = find_index(skus, target)
            if idx >= 0:
                print(f"  点击 [{idx}]: {target}")
                click_sku(idx)
                time.sleep(4)
                price = get_price()
                print(f"    价格: ¥{price}")
            else:
                print(f"  ✗ 未找到: {target}")
    
    print("\n" + "=" * 50)
    print("完成")

if __name__ == '__main__':
    main()
